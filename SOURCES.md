# Sources

## SAP Fuel and Procurement

Researched format: SAP S/4HANA purchase order OData API, especially `API_PURCHASEORDER_PROCESS_SRV`, and SAP IDoc structure as an alternative.

Sources:

- SAP Help Portal, Operations for Purchase Order: https://help.sap.com/docs/SAP_S4HANA_CLOUD/bb9f1469daf04bd894ab2167f8132a1a/46dcde53d7964b768dcf75f97f4e3db9.html
- SAP Help, IDoc Structure: https://help.sap.com/saphelp_gbt10/helpdata/en/4b/38625bad7f74fee10000000a421937/content.htm

What I learned: SAP can expose purchase order data through OData resources, while IDoc is a segment-oriented interchange format. For a four-day prototype, OData-shaped purchase order rows are more defensible than building a partial IDoc parser. Real exports often include localized labels and terse plant/material/unit fields.

Sample data: `samples/sap_fuel_procurement.csv` includes German headers, plant codes, document dates in multiple formats, litre and gallon fuel purchases, and an unmapped procurement item. This lets the app show both clean fuel rows and a row that requires analyst attention.

What would break in a real deployment: material descriptions are not enough for reliable factor mapping, plant codes need a maintained client lookup, purchase orders may be amended after import, and procurement rows may need goods receipt or invoice matching before they are considered final.

## Utility Electricity

Researched format: Green Button Download My Data / utility portal CSV exports for billing and usage data.

Sources:

- Oracle Utilities, Green Button Download My Data: https://docs.oracle.com/en/industries/utilities/digital-self-service/energy-management-overview/green-button-downloadmydata.html
- Green Button Alliance, Connect My Data overview: https://www.greenbuttonalliance.org/green-button-connect-my-data-cmd
- U.S. Department of Energy, Energy Data Management Guide: https://www.eere.energy.gov/energydataguide/step4.shtml

What I learned: Utility data commonly arrives as CSV or XML downloads, sometimes with billed usage and sometimes with interval data. Billing periods can be arbitrary and estimated reads matter.

Sample data: `samples/utility_electricity.csv` includes account number, meter number, billing dates, kWh/MWh units, tariff, and read type. One row is an estimated read and one period does not align with a calendar month.

What would break in a real deployment: PDFs and utility-specific CSV columns vary heavily, meter-to-facility mapping is not guaranteed, tariffs require separate modeling, and market-based Scope 2 would require supplier contracts or certificates.

## Corporate Travel

Researched format: SAP Concur itinerary/report style data for flights, hotels, and ground transportation.

Sources:

- SAP Help Portal, Concur Itinerary Details report fields: https://help.sap.com/docs/SAP_CONCUR/92814b27ae9c4b298c6e80d2a3241445/1c431f2e700b1014a46a108435d32877.html
- SAP Concur Developer Center, Travel Allowance APIs: https://preview.developer.concur.com/api-reference/travelallowance/v4.travelallowance-calculationresults-endpoints.html

What I learned: Concur travel/reporting data separates travel categories and can expose itinerary details such as flight number, travel source, transport vendor, hotel property, and ground transportation reservations. Distances are not guaranteed, so airport codes can be needed for flight estimation.

Sample data: `samples/concur_travel.csv` includes a flight with airport codes but no distance, a hotel stay with nights, and a ground transport row with no distance. This tests inferred values and missing-distance flags.

What would break in a real deployment: airport distance inference needs a real airport database and routing method, flights need cabin class and leg details, hotel factors need country/city, and ground transport can require vehicle type or spend-based fallback.
