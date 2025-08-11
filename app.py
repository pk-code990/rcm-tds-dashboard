import streamlit as st
import pandas as pd
from datetime import datetime

st.title("RCM GST & TDS Rent Payment Dashboard (Party-wise Aggregation)")

st.write("""
Upload an Excel/CSV file with these columns:  
**Party Name | Property Type | GST Registered | Monthly Rent | Landlord Type | Audited (Yes/No) | (Optional: Date)**  
""")

uploaded_file = st.file_uploader("Upload Excel/CSV File", type=["xlsx", "csv"])

# Detect Financial Year dynamically
today = datetime.today()
current_date = today.strftime("%d-%m-%Y")
fy = "FY 2024-25" if today.year == 2025 and today.month <= 3 else "FY 2025-26"

if uploaded_file:
    # Read the uploaded file
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

    # Check if Date column exists
    has_date_column = any(col.lower() == "date" for col in df.columns)

    # Validate required columns
    required_cols = ["Party Name", "Property Type", "GST Registered", "Monthly Rent", "Landlord Type", "Audited (Yes/No)"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"File must contain columns: {', '.join(required_cols)} (Date is optional)")
    else:
        # Determine TDS thresholds
        threshold_194i = 240000 if fy == "FY 2024-25" else 600000

        # Clean Party Name to avoid mismatch due to spaces or case
        df["Party Name Clean"] = df["Party Name"].str.strip().str.lower()

        # Calculate total annual rent per Party Name
        df["Annual Rent Total"] = df.groupby("Party Name Clean")["Monthly Rent"].transform("sum") * 12

        # Prepare output lists
        rcm_gst_list, cgst_list, sgst_list = [], [], []
        tds_list, tds_section_list, net_payable_list = [], [], []
        calc_date_list = []

        for _, row in df.iterrows():
            rent = float(row["Monthly Rent"])
            property_type = str(row["Property Type"]).strip().lower()
            gst_reg = str(row["GST Registered"]).strip().lower()
            landlord_type = str(row["Landlord Type"]).strip().lower()
            audited = str(row["Audited (Yes/No)"]).strip().lower()
            total_annual_rent = float(row["Annual Rent Total"])

            # --- Calculation Date Logic ---
            if has_date_column and pd.notnull(row.get("Date")):
                calc_date = pd.to_datetime(row["Date"]).strftime("%d-%m-%Y")
            else:
                calc_date = current_date

            # --- GST RCM Calculation ---
            rcm_gst = 0
            if property_type == "residential" and gst_reg == "no":
                rcm_gst = rent * 0.18
            elif property_type == "commercial" and gst_reg == "no":
                rcm_gst = rent * 0.18

            cgst = rcm_gst / 2
            sgst = rcm_gst / 2

            # --- TDS Calculation ---
            tds = 0
            tds_section = "N/A"

            # 194IB: Individual Non-Audited
            if landlord_type == "individual" and audited == "no":
                if rent > 50000:  # Monthly threshold for 194IB
                    tds = rent * 0.05
                    tds_section = "194IB (5%)"

            # 194I: Company / Audited Individual or Party-wise threshold breach
            else:
                if total_annual_rent > threshold_194i:  # Check based on aggregated rent
                    tds = rent * 0.10
                    tds_section = "194I (10%)"

            net_payable = rent - tds

            # Append results
            calc_date_list.append(calc_date)
            rcm_gst_list.append(rcm_gst)
            cgst_list.append(cgst)
            sgst_list.append(sgst)
            tds_list.append(tds)
            tds_section_list.append(tds_section)
            net_payable_list.append(net_payable)

        # Add calculated columns
        df["Calculation Date"] = calc_date_list
        df["Financial Year"] = fy
        df["RCM GST"] = rcm_gst_list
        df["CGST"] = cgst_list
        df["SGST"] = sgst_list
        df["TDS Section"] = tds_section_list
        df["TDS"] = tds_list
        df["Net Payable"] = net_payable_list

        # Reorder columns for output
        cols = ["Calculation Date", "Financial Year"] + [col for col in df.columns if col not in ["Calculation Date", "Financial Year", "Party Name Clean", "Annual Rent Total"]]
        df = df[cols]

        # Display results
        st.subheader(f"Calculation Result ({fy})")
        st.dataframe(df)

        # Summary
        st.write(f"**Total Rent:** ₹{df['Monthly Rent'].sum():,.2f}")
        st.write(f"**Total RCM GST:** ₹{df['RCM GST'].sum():,.2f}")
        st.write(f"**Total CGST:** ₹{df['CGST'].sum():,.2f}")
        st.write(f"**Total SGST:** ₹{df['SGST'].sum():,.2f}")
        st.write(f"**Total TDS Deducted:** ₹{df['TDS'].sum():,.2f}")

        # Downloadable Excel
        output_file = "RCM_TDS_Rent_Report.xlsx"
        df.to_excel(output_file, index=False)
        with open(output_file, "rb") as file:
            st.download_button(
                label="Download Excel Report",
                data=file,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
