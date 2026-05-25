"""Allowed upload extensions (lowercase, no dot)."""



from services.parsing.excel_parser import EXCEL_FILE_TYPES, TABLE_FILE_TYPES



ALLOWED_FILE_TYPES = frozenset(

    {

        "pdf",

        "docx",

        "xlsx",

        "xlsm",

        "xls",

        "csv",

        "txt",

    }

)



EXCEL_EXTENSIONS = EXCEL_FILE_TYPES

TABLE_EXTENSIONS = TABLE_FILE_TYPES





def extension_from_filename(filename: str) -> str:

    if "." not in filename:

        return ""

    return filename.rsplit(".", 1)[-1].lower()





def validate_upload_filename(filename: str) -> str:

    ext = extension_from_filename(filename)

    if ext not in ALLOWED_FILE_TYPES:

        allowed = ", ".join(sorted(ALLOWED_FILE_TYPES))

        raise ValueError(

            f"Unsupported file type '{ext or '(none)'}'. Allowed: {allowed}."

        )

    return ext

