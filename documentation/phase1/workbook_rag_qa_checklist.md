# Workbook RAG manual QA checklist

After deploying retrieval improvements, re-ingest the workbook (or confirm prior ingest), then ask:

1. **Reverse table definition (vague sheet)**  
   `which table name has the following table definition "Organization responsible for issuing the FOIA annual report"`  
   Expected: **Agency** (FOIA Tables).

2. **Reverse table definition (typo sheet)**  
   Same question with `FOIA Table sheet` instead of FOIA Tables.  
   Expected: **Agency**.

3. **Column + table binding**  
   `On the FOIA Fields sheet, for table SectionI-1, what is the ColumnDefinition for the column FullNameofPointofContact?`  
   Expected: report distribution (not "paper report"); table SectionI-1.

4. **Forward table definition**  
   `On the FOIA Tables sheet, what is the TableDefinition for the Application table?`  
   Expected: information system used to generate the FOIA annual report.

5. **Database metadata**  
   `On the FOIA DB sheet, what does the dictionary named AnnualReportData represent?`  
   Expected: verbatim DictionaryDescription for FOIA Annual Report.

6. **Mixed client — narrative only (citation footer)**  
   Upload narrative `.txt` files plus a workbook on the same client. Ask:  
   `who is data engineer and where does he work?`  
   Expected: answer from the `.txt` files only; UI footer **Sources** lists those filenames (e.g. `test_text1.txt; test_text2.txt`), not FOIA Tables/Fields or catalog rows.
