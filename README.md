[# Adding properties for custom reports](#properties)

Ensure that the table `custom_report_props` exists.

Run the below query.
  
* select CASE WHEN count(*)>0 THEN 'YES' ELSE 'NO' END FROM information_schema.tables WHERE lower(table_name)=lower('custom_report_props');

If it gives NO run the below command, otherwise skip this part

* bahmni -i dev -m erp run_migrations

Run the below query.

* select CASE WHEN count(*)>0 THEN 'YES' ELSE 'NO' END FROM custom_report_props WHERE name = 'mainLocationId';

If it gives NO run the below command, otherwise skip this part

* INSERT INTO custom_report_props (name,value) VALUES ('mainLocationId',(SELECT id from stock_location WHERE name = 'mainLocationName'));
* # Remember to change the mainLocationName.
* # Ex: 'BPH Storeroom'.

Run the below query.

* select CASE WHEN count(*)>0 THEN 'YES' ELSE 'NO' END FROM custom_report_props WHERE name = 'externalLocationIds';

If it gives NO run the below command, otherwise skip this part

* INSERT INTO custom_report_props (name,value) VALUES ('externalLocationIds',(SELECT id from stock_location WHERE name in (listOfExternalLocations)));
* # Remember to change the listOfExternalLocations.
* # Ex: 'Scrapped','Customers','Suppliers','BPH Scrap','BPH Expired','Inventory loss'.

# possible-erp-custom
How to depoy?
Copy the two folders to addon folder
Chown the folders to openerp
Make sure <a name="properties">properties</a> are setup
Restart the openerp
