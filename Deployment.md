# possible-erp-custom

# Steps for deployment: Follow these steps if you are deploying modules in this repository for the first time
1. Clone this repository on server using following commands:
	a. cd /opt/bahmni-erp;
	b. git clone https://github.com/Possiblehealth/possible-erp-custom.git

2. Go to path on server: cd /opt/bahmni-erp/etc

3. Open the file openerp-server.conf using vi or nano editor and add following line to it at the beginning of the line:
addons_path=/opt/bahmni-erp/possible-erp-custom,/usr/lib/python2.6/site-packages/openerp-7.0_20130301_002301-py2.6.egg/openerp/addons

4. Restart the openerp server: sudo service openerp restart

5. Go to OpenERP > Settings. Click on "Update Modules List"

6. Go to OpenERP > Settings > Apps. Search the module in "Search Text Box" located on the right and click on Enter. Remove everything else in the text box before pressing Enter

Example: "OpenERP Report" can be typed in Search box

7. Click on the module link and click "Install"

8. If no errors are thrown, module is properly installed
