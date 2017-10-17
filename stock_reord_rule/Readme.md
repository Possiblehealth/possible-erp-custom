# Usage:

1. Open any Product page and go in Procurements Section. For example: Click on OpenERP > Purchases > Products > Aceclofenac

2. You will see a new Section been added "Stock Procurement By Days" having 3 fields

	a. Days of needed warehouse stock: Number of days for which you would like to maintain the stock<br />
	b. Days of sale statistics: This module will calculate total sale for given number of days<br />
	c. Expected sales variation (percent +/-): This number will be used to increase/decrease the total required quantity as per given percentage

3. Add a default Supplier in the same section if it is not present

4. Click on Orderpoints in the top right corner of Product Section

5. Click on "Create". OpenERP will put all the default values; change the values like Warehouse, Location, etc as per the requirement and "Save". Make sure you keep "Minimum Quantity" and "Maximum Quantity" as "0.00" which is default

Above steps will have to be done for all products.

# Steps to setup cron

1. On installation of this module, it will create two Schedulers in section: Openerp > Settings > Scheduler > Scheduled Actions with a name: "Update quantity for reordering rules" and "Run Purchase Scheduler"

2. Interval Unit: Can be changed to Minutes, Hours, Days, Weeks, Months

3. Interval Number: This is the frequency of occurrence for above unit

Keep other settings unchanged.

# Impact Areas

As and when the cron will run, depending on the current available stock quantity, Days of needed warehouse stock, Days of sale statistics, Expected sales variation; this module will update Minimum Quantity and Maximum Quantity in OpenERP > Warehouse > Configuration > Reordering Rules

# Action to be taken for creating Purchase Order - Manual (Cron will create PO in draft mode as per the set frequency in above steps)

1. Click on OpenERP > Warehouse > Schedulers > Run Scheduler(tick "Automatic Orderpoint"). 

2. Above step will create Purchase Orders in OpenERP > Purchases > Quotation in draft mode for all product whose Available stock quantity is below minimum/maximum quantity in Reordering Rules

3. Select all Quotations which belong to same supplier and click on More > Merge Purchase Orders for single Purchase Order of multiple products