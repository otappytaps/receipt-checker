# receipt-checker

A Python script utilizing Google OAuth 2.0 to check receipt images on a user's behalf using Sheets API and Drive API via Google Cloud.

---

### Requirements

- **[Python](https://www.python.org/) Version 3.12+**
- **[PaddleOCR](https://github.com/PADDLEPADDLE/PADDLEOCR)**
- **[pip](https://pypi.org/project/pip/)**
- **[Google Cloud](https://cloud.google.com) Account**

---

### How it works

The script a Google Sheets spreadsheet given that it has the following **columns**:

- **Google Drive Link of the receipt image**
- **Reference number of the receipt**
- **Status**

At every given row, the script extracts the **reference number** and **amount paid** from the receipt image in the Google Drive link _(in which the script downloads the image file and deletes it after it is processed)_.

The extracted reference number is then compared to the reference number given in the row, while the amount paid is then compared to the hard-coded amount.

The script will write `Pass` on the **Status** column if both values match. If the reference number from the image does not match the reference number given in the row, it will write `Fail - Invalid Reference No.`. If the amount paid extracted from the receipt image does not match the hard-coded amount, it will write `Fail - Invalid Amount Paid`. In the instance that both values are invalid, it will write `Fail - Invalid Reference No. and Amount Paid`.

For every run of the script, it will create a _.txt_ **log file** containing internal values and results that were processed in each row which are the following:

- **Ref No.**: Extracted reference number from the receipt image in lower case.
- **Amt Paid**: Extracted amount paid from the receipt image.
- **Err Ref No.**: _True_ if there is there is a reference number mismatch, _False_ if none.
- **Err Amt Paid**: _True_ if there is there is an amount paid mismatch, _False_ if none.
- **Status**: Value that was written in the Google Sheets spreadsheet's Status column.

#### Example:

```
[Row 2] Ref No: 1234567890 | Amt Paid: 200.0 | Err Ref No: False | Err Amt Paid: True | Status: Fail - Invalid Amount Paid
```

Log files of the script could be found in the **logs** folder in the script's directory and is named accordingly to when the script was ran in this format: `YYYY-MM-DD_HH-MM-SS.txt`.

During runtime, the script also displays the same logs in the terminal as it processes each row.

---

### Getting Started

Install the following external packages on the terminal.

```bash
pip install gspread paddleocr paddlepaddle google-api-python-client google-auth google-auth-oauthlib
```

<br>

Once downloaded, view the `main.py` file and you will see the following on **lines 16-28**:

```python
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
```

Edit the variables marked with `#TODO` according to your sheets.

**Note**: `SPREADSHEET_ID` refers to the string enclosed in `/` after `/d` in the spreadsheet's url.

A [Google Cloud](https://cloud.google.com) project must also be set up to handle the API calls of the script. Make sure to enable **Google Sheets API** and **Google Drive API** in the project settings on the console.

Additionally, a _.json_ file is also needed to authorize script access to the your Google files via OAuth 2.0. You can get this by going to your [Google Cloud](https://cloud.google.com) console and creating a **Credential** which will prompt you to download a _.json_ file upon completion. Put this _.json_ file in the same directory as the script and rename it as `credentials.json`.

To run the script, open the terminal in the script's directory and enter the following:

```bash
python main.py
```

---

### Notes

- OCR is instantiated in the language **English** in **line 152**. To change it, edit the `lang` argument, or delete it for multi-language support.
  <br>
- Due to compatibility issues, CPU accelaration is disabled for the OCR. However, this can be enabled back in **line 152** by setting the `enable_mkldnn` to `True`.
