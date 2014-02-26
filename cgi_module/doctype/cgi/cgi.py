# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
sql = webnotes.conn.sql
from webnotes.model.doc import Document, addchild
from  selling.doctype.customer.customer import DocType

from webnotes.utils import cstr, cint, flt, comma_or,add_days, cint, cstr, date_diff, flt, getdate, nowdate, \
        get_first_day, get_last_day,nowtime
from datetime import date,timedelta
import datetime
from webnotes import msgprint
from webnotes.model.doc import Document



class DocType():
        def __init__(self, d, dl):
                self.doc, self.doclist = d, dl

        def make_customer(self,args):
	
		for i in range(0,len(args)):
			if (args[i])['Customer Name']:
				check_customer=sql("select name from tabCustomer where name='"+(args[i])['Customer Name']+"'")
				if not check_customer:
					self.create_customer(args[i])
					self.create_account_head(args[i])
					#self.create_si(args[i])	
                return "Done"

	def create_si(self,args):
		for i in args:
			if i=='Customer Name':
				si=Document('Sales Invoice')
				si.customer=args['Customer Name']
				si.save()		
				sic=Document('Sales Invoice Item')
				for j in range(0,len(args['Child'])):
					sic.item_code=(args['Child'])[j]['item_name']
					sic.qty=(args['Child'])[j]['qty']
					sic.parentfield='entries'
					sic.parenttype='Sales Invoice'
					webnotes.errprint(si.name)
					sic.parent=si.name
					sic.save(new=1)
				

	def make_po(self,args):
		net_tot=0.00
		for i in range(0,len(args)):
				po=Document('Purchase Order')
                		po.transaction_date=nowdate()
				po.price_list_currency='INR'
				po.currency='INR'
				po.buying_price_list='Standard Buying'
				po.customer_name=args[i]['Customer Name']
				po.contact=args[i]['Contact Number']
				po.status='Draft'
				po.company='InnoWorth'
				po.conversion_rate=1.00
                                po.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
				po.docstatus=0
				po.plc_conversion_rate=1
                                po.save()
                                sic=Document('Purchase Order Item')
                                for j in range(0,len(args[i]['Child'])):                                      
					if (args[i]['Child'])[j]['Item Name']:
						pre_doc=webnotes.conn.sql("select a.parent,a.warehouse,a.item_name,a.uom,a.description,a.ordered_qty,a.name from `tabMaterial Request Item` a ,`tabMaterial Request` b where a.item_code='"+(args[i]['Child'])[j]['Item Name']+"' and a.parent=b.name and b.docstatus=1 and a.qty<>a.ordered_qty limit 1",as_list=1)
						if pre_doc:
							sic.item_code=(args[i]['Child'])[j]['Item Name']
                                        		sic.qty=(args[i]['Child'])[j]['Qty']
							sic.stock_qty=(args[i]['Child'])[j]['Qty']
                                        		sic.schedule_date=(args[i]['Child'])[j]['Required Date']
							sic.prevdoc_docname=pre_doc[0][0]
							sic.warehouse=pre_doc[0][1]
							sic.item_name=pre_doc[0][2]
							sic.uom=pre_doc[0][3]
							sic.stock_uom=pre_doc[0][3]
							sic.description=pre_doc[0][4]
							sic.prevdoc_detail_docname=pre_doc[0][6]
							sic.conversion_factor=1.0
							sic.prevdoc_doctype='Material Request'
							rate=webnotes.conn.sql("select ref_rate from `tabItem Price` where price_list='Standard Buying' and item_code='"+(args[i]['Child'])[j]['Item Name']+"'",as_list=1)
							if rate:
								sic.import_ref_rate=rate[0][0]
								sic.import_rate=rate[0][0]
							else:
								sic.import_ref_rate=1
                                                        	sic.import_rate=1
							if (args[i]['Child'])[j]['Qty']:
								sic.import_amount=cstr(flt(sic.import_ref_rate)*flt((args[i]['Child'])[j]['Qty']))
							else:
								sic.import_amount=sic.import_ref_rate
							net_tot=cstr(flt(sic.import_amount)+flt(net_tot))
                                        		sic.parentfield='po_details'
                                        		sic.parenttype='Purchase Order'                                  
                                        		sic.parent=po.name
                                        		sic.save(new=1)
				po_=Document('Purchase Order',po.name)
				po_.net_total_import=net_tot
				po_.grand_total_import=net_tot
				po_.rounded_total=net_tot
           			po_.save()
				return "Done"
			

	def create_customer(self,args):
		for i in args:
				if i=='Customer Name':		
					#import webbrowser
			                #webbrowser.open('http://192.168.5.5:7777/server.py?cmd=login&usr=administrator&pwd=admin')
                			d = Document('Customer')
                			d.customer_name = args['Customer Name']           
					d.name=args['Customer Name']
                			d.save()		
					

	def create_account_head(self,args):
		company='InnoWorth'
		abbr = 'innow'
			
		for i in args:                   
				if not webnotes.conn.exists("Account", (args['Customer Name'] + " - " + abbr)):
                                	parent_account = 'Accounts Receivable - innow'
	
                                	d = Document('Account')
                                	d.account_name = args['Customer Name']
                                	d.parent_account= parent_account
                                        d.group_or_ledger='Ledger'
                                        d.company=company
                                        d.master_type='Customer'
					d.debit_or_credit='Debit'
					d.is_pl_account='No'
                                        d.master_name=args['Customer Name']
                                        d.freeze_account= "No"
                                	d.save()		
