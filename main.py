import os
import re
import tempfile
import gspread

from pathlib import Path
from datetime import datetime
from paddleocr import PaddleOCR
from googleapiclient.discovery import Resource
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow


# TODO: Replace with your own spreadsheet ID
SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE'

# TODO: Replace with your own sheet name
SHEET_NAME = 'YOUR_SHEET_NAME_HERE'

# TODO: Replace with your own column numbers (1-based indexing)
DRIVE_LINK_COL = None
REF_NUM_COL = None  
STATUS_COL = None

# TODO: Replace with your own amount
AMOUNT_PAID = None

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]


def get_logPath() -> Path:
    """
    Returns a Path object that will be used to create the log file named according to the date and time of when the script was ran.

    Returns: 
        Path: An object that points to the log file.

    Format: YYYY-MM-DD_HH-MM-SS.txt

    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = Path("logs/") / f"{timestamp}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)

    return path

def get_creds() -> Credentials:
    """
    Prompts user login to Google and returns a Credentials object for file access authorization when login is successful.

    """
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES
    )

    creds = flow.run_local_server(port=0)
    return creds

def get_fileId(url: str) -> str:
    """
    Returns a file's ID as a string given its Google Drive link.

    Args:
        url (str): The link to the file in Google Drive.
    
    Returns:
        str: The ID of the file.

    Raises:
        ValueError: If the link is not a valid Google Drive link.

    """
    match = re.search(r'(?:/d/|id=|/file/d/)([a-zA-Z0-9_-]{15,})', url)
    if match:
        return match.group(1)
    raise ValueError(f"Unable to parse fileId from URL: {url}")

def download_file(drive_service: Resource, file_id: str, output_path: str):
    """
    Downloads a file by its ID through Google Drive API and saves it in a specified path.

    Args: 
        drive_service (Resource): A Resource object that is used to make requests to the Google Drive API.
        file_id (str): The ID of the file to be downloaded.
        output_path (str): The path where the file will be saved.

    """
    req = drive_service.files().get_media(fileId=file_id)
    with open(output_path, "wb") as f:

        # the downloader downloads the file in binary chunks
        downloader = MediaIoBaseDownload(f, req)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

def get_ref_no(txt: str) -> str:
    """
    Returns the reference number of a receipt as a string given its text using regex.

    Args:
        txt (str): The text of the receipt.

    Returns:
        str: The reference number of the receipt.

    Raises:
        ValueError: If the reference number cannot be parsed from the text.
    
    """
    match  = re.search(r'(?:Ref\s*No|Reference\s*no)[\s.\n:]*([A-Z0-9\-]+)', txt, re.IGNORECASE)
    if match:
        return match.group(1)
    raise ValueError(f"Unable to parse reference number from text: {txt}")

def get_amt_paid(txt: str) -> str:
    """
    Returns the amount paid of a receipt as a string given its text using regex.

    Args:
        txt (str): The text of the receipt.

    Returns:
        str: The amount paid of the receipt.

    Raises: 
        ValueError: If the amount paid cannot be parsed from the text.
    
    """
    match  = re.search(r'(?:PHP|\bP(?![A-Z])|₱)[\s\n]*([\d,]+(?:\.[\d]{1,2})?)', txt, re.IGNORECASE)
    if match:
        return match.group(1)
    raise ValueError(f"Unable to parse amount paid from text: {txt}")


def main():
    try:
        creds = get_creds()
        gc = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)

        logPath = get_logPath()
        f = open(logPath, 'w')

        # Disabled mkldnn as it cause compatibility issues in some machines
        ocr = PaddleOCR(use_textline_orientation=False, ocr_version='PP-OCRv4', lang='en', enable_mkldnn=False)
        sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        rows = sheet.get_all_values()

        # skips 1 row for header
        for row_idx, row in enumerate(rows[1:], start=2):
            drive_link = row[DRIVE_LINK_COL-1] if len(row) >= DRIVE_LINK_COL else ''
            ref_num = row[REF_NUM_COL-1] if len(row) >= REF_NUM_COL else ''
            cur_status = row[STATUS_COL-1] if len(row) >= STATUS_COL else ''

            if cur_status == "Pass":
                continue

            if not drive_link:
                sheet.update_cell(row_idx, STATUS_COL, "Missing Drive Link")
                continue

            if not ref_num:
                sheet.update_cell(row_idx, STATUS_COL, "Missing Reference No.")
                continue

            temp_path = None
            try:
                fileId = get_fileId(drive_link)
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_path = temp_file.name
                temp_file.close()
                download_file(drive_service, fileId, temp_path)

                ocr_result = ocr.predict(temp_path)

                if ocr_result and ocr_result[0]:
                    result_text = "\n".join(ocr_result[0]['rec_texts'])
                else:
                    raise ValueError(f"OCR is not able to extract text from image: {temp_path}")

                ref_num = ref_num.replace(' ', '').lower()
                rec_ref_num = get_ref_no(result_text).replace(' ', '').lower()
                amt_paid = float(get_amt_paid(result_text).replace(',', ''))

                err_ref_num = rec_ref_num != ref_num
                err_amt_paid = amt_paid != AMOUNT_PAID


                if (err_ref_num and err_amt_paid):
                    final_status = "Fail - Invalid Reference No. and Amount Paid"
                elif (err_ref_num):
                    final_status = "Fail - Invalid Reference No."
                elif (err_amt_paid):
                    final_status = "Fail - Invalid Amount Paid"
                else:
                    final_status = "Pass"

                sheet.update_cell(row_idx, STATUS_COL, final_status)

                # log through terminal and file
                log = f"[Row {row_idx}] Ref No: {rec_ref_num} | Amt Paid: {amt_paid} | Err Ref No: {err_ref_num} | Err Amt Paid: {err_amt_paid} | Status: {final_status}"
                print(log)
                f.write(log+'\n')

            except Exception as e:
                print(f"[Row {row_idx}] Error: {e}")
                sheet.update_cell(row_idx, STATUS_COL, f"Error: {str(e)}")

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
    finally:
        if f is not None:
            f.close()

if __name__ == "__main__":
    main()