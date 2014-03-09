#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
sql = webnotes.conn.sql
from webnotes.model.doc import Document, addchild
from  selling.doctype.customer.customer import DocType

from webnotes.utils import cstr, cint, flt, comma_or,add_days, cint, cstr, date_diff, flt, getdate, nowdate, \
        get_first_day, get_last_day,nowtime,auth,document_attach
from datetime import date,timedelta
from utilities.transaction_base import get_default_address, get_address_display
import datetime
from webnotes import msgprint
from webnotes.model.doc import Document
from webnotes.utils.html_file import html_data
import os


class DocType():
        def __init__(self, d, dl):
                self.doc, self.doclist = d, dl

	def customer(self,args):
		s=self.validate_customer(args)
                if s[1]=="error":
                        return s[0]
                else:
                        msg=self.make_customer(args)
                        return msg

        def make_customer(self,args):
		for s in args:
			check_customer=sql("select name from tabCustomer where name='"+(s['Customer Name']).strip() +' - '+(s['Id']).strip()+"'")
			if not check_customer:
                                        name=self.create_customer(s)
                                        self.create_account_head(s)
                                        self.create_contact(name,s)                                     
                                        self.create_address(name,s)
                                        message="Done"
                        else:
                                        message="Customer is already exist"
                return message

	def create_contact(self,name,args):
			c=Document('Contact')
			c.customer_name=args['Customer Name']
			c.first_name=name
			c.customer=name
			c.email_id=args['Email Id']
			c.phone=args['Phone Number']
			c.is_primary_contact=1
			c.save()

	def create_address(self,name,args):
			c=Document('Address')
                        c.address_line1=args['Address']
                        c.address_type='Shipping'
                        c.customer=name
			c.customer_name=args['Customer Name']
			c.address_title=name
                        c.city=args['City']
                        c.phone=args['Phone Number']
			c.state=args['State']
			c.country=args['Country']
			c.pincode=args['Pincode']
                        c.is_primary_address=1
                        c.save()

	def create_si(self,args):
		for i in args:
			if i['Type']=="Sales Order":
				check_so=sql("select name from `tabSales Order` where name='"+i['Sales Order No']+"'")
                                if check_so:
                                        a=self.make_si(i)
					
                                else:
                                        a={"Error":"Sales order number is not exist"}
			else:
				validate=self.validate_si(i)
				if validate[1]=="error":
	                	        return validate
        		        else:
                		        a=self.service_si(i)                		   
                	        	return a
                return a
		

	def service_si(self,s):
		total_amt=0.00
		si=Document("Sales Invoice")
                si.customer=webnotes.conn.get_value("Customer",{"innoworth_id":(s['Customer Id']).strip()},"name")
                si.customer_name=webnotes.conn.get_value("Customer",{"innoworth_id":(s['Customer Id']).strip()},"name")
                si.posting_date=nowdate()
                si.due_date=nowdate()
                si.company='InnoWorth'
                si.conversion_rate=1.00
                si.customer_group='Individual'
                si.territory=s['Territory']
                si.debit_to=webnotes.conn.get_value('Account',{"master_name":si.customer},'name')
                si.price_list_currency='INR'
                si.currency='INR'
                si.selling_price_list='Standard Selling'
                si.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")               
                si.docstatus=1
                si.save()
		html=""
		j=0
                for r in s['Child']:
			j=j+1
			child_data=sql("select name,item_name,item_group,description,stock_uom from `tabItem` where name='"+(r['Item Name']).strip()+"'",as_list=1)
                	sic=Document("Sales Invoice Item")
                        sic.parent=si.name
                        sic.item_code=child_data[0][0]
			sic.item_name=child_data[0][1]
                        sic.item_group=child_data[0][2]
                        sic.description=child_data[0][3]
                        sic.qty=(r['Qty']).strip()
                        sic.stock_uom=child_data[0][4]
                        sic.ref_rate=webnotes.conn.get_value("Item Price",{"item_code":(r['Item Name']).strip(),"price_list":"Standard Selling"},"ref_rate")
			sic.export_rate=webnotes.conn.get_value("Item Price",{"item_code":(r['Item Name']).strip(),"price_list":"Standard Selling"},"ref_rate")
			if child_data[0][1]:
                                sic.export_amount=cstr(flt(sic.ref_rate)*flt((r['Qty']).strip()))
                        else:
                                sic.export_amount=cstr((r['Qty']).strip())
			total_amt=cstr(flt(total_amt)+flt(sic.export_amount))
                        sic.income_account='Sales - innow'
                        sic.cost_center='Main - innow'
                        sic.docstatus=1
                        sic.save()
			html+=("<tr><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(j)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.item_code)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.description)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;text-align:right;'><div>"+cstr(sic.qty)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.stock_uom)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align:right'>₹ "+cstr(sic.ref_rate)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align: right'>₹ "+cstr(sic.export_amount)+"</div></td></tr>")

		si_=Document('Sales Invoice',si.name)
		si_.net_total_export=cstr(total_amt)
                si_.grand_total_export=cstr(total_amt)
                si_.rounded_total_export=cstr(total_amt)
		si_.save()

                data=[{"account":si.debit_to,"debit":si_.net_total_export,"credit":"0","against":"Sales - innow","against_voucher_type":"Sales Invoice","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":""},{"account":'Sales - innow',"debit":"0","credit":si_.net_total_export,"against":si.debit_to,"against_voucher_type":"","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":"Main - innow"}]
                self.create_gl(data)
		a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"customer_name":si.customer_name,"net_total":si_.net_total_export,"grand_total":si_.grand_total_export,"rounded_total":si_.rounded_total_export,"table_data":html,"date_1":"Posting Date","date_2":"Due Date","doctype":"Sales Invoice","doctype_no":si.name,"company":si.company,"addr_name":"","address":"","tax_detail":""})
                attach_file(a,[si.name,"Account/Kirana","Sales Invoice"])
                return {"Sales Invoice":si.name}


	def make_si(self,args):
			parent=sql("select * from `tabSales Order` where name='"+(args['Sales Order No']).strip()+"'",as_dict=1)
			if parent:
				for r in parent:
					si=Document("Sales Invoice")
					si.customer=r['customer']
					si.customer_name=r['customer_name']
					si.posting_date=nowdate()
					si.due_date=nowdate()
					#si.status='Submitted'
               		 	        si.company='InnoWorth'
            	 			si.conversion_rate=1.00
                        		si.customer_group='Individual'
					si.territory=r['territory']
					si.debit_to=webnotes.conn.get_value('Account',{"master_name":r['customer']},'name')
					si.price_list_currency='INR'
                        		si.currency='INR'
                        		si.selling_price_list='Standard Selling'
					si.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
					si.net_total_export=cstr(r['net_total_export'])
                        		si.grand_total_export=cstr(r['grand_total_export'])
                        		si.rounded_total_export=cstr(r['rounded_total_export'])
					si.docstatus=1	
					update=sql("update `tabSales Order` set per_billed='100' where name='"+cstr(r['name'])+"'")
					si.save()
					child=sql("select * from `tabSales Order Item` where parent='"+(args['Sales Order No']).strip()+"'",as_dict=1)
					html=""
					j=0
					for s in child:
						j=j+1
						sic=Document("Sales Invoice Item")
						sic.parent=si.name
						sic.item_code=s['item_code']
						sic.item_name=s['item_name']
						sic.item_group=s['item_group']
						sic.description=s['description']
						sic.qty=s['qty']
						sic.stock_uom=s['stock_uom']
						sic.ref_rate=s['ref_rate']
						sic.amount=s['export_amount']
						sic.export_rate=s['export_rate']
						sic.export_amount=s['export_amount']
						sic.income_account='Sales - innow'
						sic.cost_center='Main - innow'
						sic.warehouse=s['reserved_warehouse']
						sic.sales_order=r['name']
						sic.so_detail=s['name']
						sic.docstatus=1
						html+=("<tr><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(j)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.item_code)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.description)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;text-align:right;'><div>"+cstr(sic.qty)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.stock_uom)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align:right'>₹ "+cstr(sic.ref_rate)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align: right'>₹ "+cstr(sic.export_amount)+"</div></td></tr>")
						update=sql("update `tabSales Order Item` set billed_amt='"+cstr(s['export_amount'])+"' where name='"+cstr(s['name'])+"'")
						sic.save()
					data=[{"account":si.debit_to,"debit":si.net_total_export,"credit":"0","against":"Sales - innow","against_voucher_type":"Sales Invoice","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":""},{"account":'Sales - innow',"debit":"0","credit":si.net_total_export,"against":si.debit_to,"against_voucher_type":"","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":"Main - innow"}]
					self.create_gl(data)
					a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"customer_name":si.customer_name,"net_total":si.net_total_export,"grand_total":si.grand_total_export,"rounded_total":si.rounded_total_export,"table_data":html,"date_1":"Posting Date","date_2":"Due Date","doctype":"Sales Invoice","doctype_no":si.name,"company":si.company,"addr_name":"","address":"","tax_detail":""})
                        		attach_file(a,[si.name,"Account/Kirana","Sales Invoice"])
					return {"Sales Invoice":si.name}

	def create_gl(self,data):
		for r in data:
			gl=Document("GL Entry")
			gl.account=r['account']
			gl.debit=r['debit']
			gl.credit=r['credit']
			gl.against=r['against']
			gl.against_voucher_type=r['against_voucher_type']
			gl.voucher_type=r['voucher_type']
			gl.voucher_no=r['voucher_no']
			gl.cost_center=r['cost_center']
			gl.posting_date=nowdate()
			gl.aging_date=nowdate()
			gl.fiscal_year=webnotes.conn.get_value("Global Defaults",None,"current_fiscal_year")
			gl.company='InnoWorth'
			gl.is_opening='No'
			gl.save()
			

	def create_po(self,args):
		s=self.validate_po(args)
		if s[1]=="error":
			return s[0]
		else:
			for r in args:	
				po=self.make_po(r)
				so=self.make_so(r)
			return [po,so]


	def make_so(self,args):
		# coding: utf-8
		net_tot=0.00
		so=Document('Sales Order')
                so.transaction_date=nowdate()
                so.price_list_currency='INR'
                so.currency='INR'
                so.selling_price_list='Standard Selling'
                so.customer=webnotes.conn.get_value("Customer",{"innoworth_id":(args['Customer Id']).strip()},"name")
                so.customer_name=webnotes.conn.get_value("Customer",{"innoworth_id":(args['Customer Id']).strip()},"customer_name")
                so.delivery_date=(args['Required Date']).strip()
                so.company='InnoWorth'
                so.conversion_rate=1.00
                so.customer_group='Individual'
                if (args['Territory']).strip():
                	so.territory=(args['Territory']).strip()
                so.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
                so.customer_address=webnotes.conn.get_value("Address",{"customer":so.customer},"name")
		so.address_display=get_address_display(so.customer_address)
                so.contact_person=webnotes.conn.get_value("Contact",{"customer":so.customer},"name")
                so.docstatus=1
                so.status='Submitted'
                so.plc_conversion_rate=1
                so.save()
                html=""
		sr=0
                for j in args['Child']:
				sr=sr+1
                                soi=Document('Sales Order Item')
                                soi.item_code=(j['Item Name']).strip()
                                soi.qty=(j['Qty']).strip()
				item_details=webnotes.conn.sql("select default_warehouse,item_name,stock_uom,description from tabItem where name='"+(j['Item Name']).strip()+"'",as_list=1)
                                soi.reserved_warehouse=item_details[0][0]
                                soi.item_name=item_details[0][1]                             
                                soi.stock_uom=item_details[0][2]
                                soi.description=item_details[0][3]
                                rate=webnotes.conn.sql("select ref_rate from `tabItem Price` where price_list='Standard Selling' and item_code='"+(j['Item Name']).strip()+"'",as_list=1)
                                if rate:
                                        soi.ref_rate=rate[0][0]
                                        soi.export_rate=rate[0][0]
                                else:
                                        soi.ref_rate=1
                                        soi.export_rate=1
                                soi.export_amount=cstr(flt(soi.ref_rate)*flt((j['Qty']).strip()))
                                net_tot=cstr(flt(net_tot)+flt(soi.export_amount))
                                soi.parentfield='sales_order_details'
                                soi.parenttype='Sales Order'
                                soi.docstatus=1
                                soi.parent=so.name
                                soi.save(new=1)
                                html+=("<tr><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sr)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(soi.item_code)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(soi.description)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;text-align:right;'><div>"+cstr(soi.qty)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(soi.stock_uom)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align:right'>₹ "+cstr(soi.ref_rate)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align: right'>₹ "+cstr(soi.export_amount)+"</div></td></tr>")
                                data=[]
                                data.append({"item_code":soi.item_code,"so_qty":soi.qty,"proj_qty":(0-flt(soi.qty)),"warehouse":soi.reserved_warehouse,"bin_iqty":"","bin_pqty":"Bin.projected_qty","type":"so"})
                                self.update_bin(data)
                so_=Document("Sales Order",so.name)
                so_.net_total_export=net_tot
                so_.grand_total_export=net_tot
                so_.rounded_total_export=net_tot
                so_.save()
                a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":datetime.datetime.strptime(so.delivery_date,'%Y-%m-%d').strftime('%d/%m/%Y'),"customer_name":so.customer_name,"net_total":net_tot,"grand_total":net_tot,"rounded_total":net_tot,"table_data":html,"date_1":"Sales Order Date","date_2":"Expected Delivery Date","doctype":"Sales Order","doctype_no":so.name,"company":so.company,"addr_name":"Customer Address","address":so.address_display,"tax_detail":""})
                attach_file(a,[so.name,"Selling/Kirana","Sales Order"])
                return {"Sales Order":so.name}
		

	def make_po(self,args):
			net_tot=0.00
			po=Document('Purchase Order')
                        po.transaction_date=nowdate()
                        po.price_list_currency='INR'
                        po.currency='INR'
                        po.buying_price_list='Standard Buying'
                        po.customer_detail=webnotes.conn.get_value("Customer",{"innoworth_id":(args['Customer Id']).strip()},"name")
                        po.customer_name=webnotes.conn.get_value("Customer",{"innoworth_id":(args['Customer Id']).strip()},"customer_name")
                        if (args['Territory']).strip():
                        	supplier=sql("select name from tabSupplier where territory='"+(args['Territory']).strip()+"'",as_list=1)
                                if len(supplier)>=1:
                                	po.supplier=supplier[0][0]                    
                        po.status='Draft'
                        po.company='InnoWorth'
                        po.conversion_rate=1.00
                        po.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
			po.customer_address_data=webnotes.conn.get_value("Address",{"customer":po.customer_detail},"name")
                	po.customer_address=get_address_display(po.customer_address_data)
                        po.docstatus=0
                        po.plc_conversion_rate=1
                        po.save()
			for data_c in args['Child']:
				if (data_c['Item Name']).strip() and (data_c['Qty']).strip():
                                                        pre_doc=webnotes.conn.sql("select a.parent as parent,ifnull(a.ordered_qty,0) as ordered_qty,a.name as name,a.qty as qty from `tabMaterial Request Item` a ,`tabMaterial Request` b where a.item_code='"+(data_c['Item Name']).strip()+"' and a.parent=b.name and b.docstatus=1 and a.qty<>ifnull(a.ordered_qty,0) and a.qty<>0",as_list=1)
                                                        item_details=webnotes.conn.sql("select default_warehouse,item_name,stock_uom,description from tabItem where name='"+(data_c['Item Name']).strip()+"'",as_list=1)
                                                        order_qty=cstr((data_c['Qty']).strip())
                                                        i=0
                                                       
                                                        for s in pre_doc:
                                                                pi_qty=webnotes.conn.sql("select ifnull(sum(qty),0) from `tabPurchase Order Item` where prevdoc_docname='"+pre_doc[i][0]+"' and prevdoc_detail_docname='"+pre_doc[i][2]+"' and docstatus=0",as_list=1)
                                                                if pi_qty:
                                                                        available_qty=cstr(cint(pre_doc[i][3])-cint(pre_doc[i][1])-cint(pi_qty[0][0]))
                                                                else:
                                                                        available_qty=cstr(cint(pre_doc[i][3])-cint(pre_doc[i][1]))
                                                                if cint(available_qty) >= cint(order_qty):
                                                                        child_data=[]           
                                                                        child_data.append([(data_c['Item Name']).strip(),order_qty,(args['Required Date']).strip(),pre_doc[i][0],item_details[0][0],item_details[0][1],item_details[0][2],item_details[0][3],pre_doc[i][2],po.name])
                                                                        value1=self.create_child_po(child_data)
                                                                        net_tot=cstr(flt(net_tot)+flt(value1))
                                                                        order_qty=0
                                                                        break;
                                                                else:
                                                                        child_data=[]
                                                                        if cint(available_qty)>0:
                                                                                child_data.append([(data_c['Item Name']).strip(),available_qty,(args['Required Date']).strip(),pre_doc[i][0],item_details[0][0],item_details[0][1],item_details[0][2],item_details[0][3],pre_doc[i][2],po.name])
                                                                
                                                                                value2=self.create_child_po(child_data)
                                                                                net_tot=cstr(flt(net_tot)+flt(value2))
                                                                                order_qty=cint(order_qty)-cint(available_qty)
                                                                        i=i+1
                                                                
                                                        if cint(order_qty)!=0:
                                                                child_data=[]
                                                                child_data.append([(data_c['Item Name']).strip(),order_qty,(args['Required Date']).strip(),item_details[0][0],item_details[0][1],item_details[0][2],item_details[0][3],po.name])
								value3=self.create_material_request(child_data)
                                                                net_tot=cstr(flt(net_tot)+flt(value3))
                                
                        po_=Document('Purchase Order',po.name)
                        po_.net_total_import=net_tot
                        po_.grand_total_import=net_tot
                        po_.rounded_total=net_tot
                        po_.save()
                             
                        return {"Purchase Order":po.name}

	def create_child_po(self,child_data):	
			sic=Document('Purchase Order Item')
			sic.item_code=child_data[0][0]
                        sic.qty=child_data[0][1]
                        sic.stock_qty=child_data[0][1]
                        sic.schedule_date=child_data[0][2]
                        sic.prevdoc_docname=child_data[0][3]
                        sic.warehouse=child_data[0][4]
                        sic.item_name=child_data[0][5]
                        sic.uom=child_data[0][6]
                        sic.stock_uom=child_data[0][6]
                        sic.description=child_data[0][7]
                        sic.prevdoc_detail_docname=child_data[0][8]
                        sic.conversion_factor=1.0
                        sic.prevdoc_doctype='Material Request'
                        rate=webnotes.conn.sql("select ref_rate from `tabItem Price` where price_list='Standard Buying' and item_code='"+child_data[0][0]+"'",as_list=1)
                        if rate:
                        	sic.import_ref_rate=rate[0][0]
                                sic.import_rate=rate[0][0]
                        else:
                                sic.import_ref_rate=1
                                sic.import_rate=1
                        if child_data[0][1]:
                        	sic.import_amount=cstr(flt(sic.import_ref_rate)*flt(child_data[0][1]))
                        else:
                        	sic.import_amount=sic.import_ref_rate                    
                        sic.parentfield='po_details'
                        sic.parenttype='Purchase Order'                                  
                        sic.parent=child_data[0][9]
                        sic.save()
			return sic.import_amount

	def create_material_request(self,args):				
				mr=Document('Material Request')
				mr.material_request_type='Purchase'
				mr.naming_series='MREQ-'
				mr.company='InnoWorth'
				mr.transaction_date=nowdate()
				mr.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")
				mr.status='Submitted'
				mr.docstatus=1
				mr.save()
				mrc=Document('Material Request Item')
				mrc.parent=mr.name
				mrc.item_code=args[0][0]
				mrc.qty=args[0][1]
				mrc.schedule_date=args[0][2]		
				mrc.docstatus=1
				mrc.warehouse=args[0][3]
				mrc.item_name=args[0][4]
				mrc.uom=args[0][5]
				mrc.description=args[0][6]
				mrc.parentfield='indent_details'
				mrc.parenttype='Material Request'
				mrc.save()
				child_data=[]
                                child_data.append([mrc.item_code,mrc.qty,mrc.schedule_date,mr.name,mrc.warehouse,mrc.item_name,mrc.uom,mrc.description,mrc.name,args[0][7]])
				
				data=[]
				data.append({"item_code":mrc.item_code,"so_qty":cstr(mrc.qty),"proj_qty":('+'+cstr(mrc.qty)),"warehouse":mrc.warehouse,"bin_iqty":"Bin.indented_qty","bin_pqty":"Bin.projected_qty","type":"po"})
				self.update_bin(data)
                                import_amount=self.create_child_po(child_data)
				return import_amount

	def update_bin(self,data):
		for d in data:
			check=webnotes.conn.sql("select name from tabBin where warehouse='"+d['warehouse']+"' and item_code='"+d['item_code']+"'",as_list=1)
			if check:
				
				if d['type']=='po':
					update=sql("update tabBin set indented_qty=indented_qty+"+cstr(d['so_qty'])+",projected_qty=projected_qty"+cstr(d['proj_qty'])+" where name='"+check[0][0]+"'")
				else:
					update=sql("update tabBin set reserved_qty=reserved_qty+"+d['so_qty']+",projected_qty=projected_qty"+cstr(d['proj_qty'])+" where name='"+check[0][0]+"'")
				
			else:
				Bin=Document('Bin')
                                Bin.warehouse=d['warehouse']
                                Bin.item_code=d['item_code']
                                d['bin_iqty']=cstr(d['so_qty'])
				d['bin_pqty']=cstr(d['proj_qty'])
				Bin.stock_uom=webnotes.conn.get_value("Item", d['item_code'], "stock_uom")
                                Bin.save()

	def create_customer(self,args):
		d = Document('Customer')
                d.customer_name = args['Customer Name']
                d.innoworth_id=args['Id']
                d.customer_type='Individual'
                d.customer_group='Commercial'
                d.territory='India'
                d.company='InnoWorth'
                d.save()        
                return d.name		

	def create_account_head(self,args):
		company='InnoWorth'
		abbr = 'innow'
		parent_account = 'Accounts Receivable - innow'
                name=args['Customer Name']+' - '+args['Id']
                d = Document('Account')
                d.account_name = name
                d.parent_account= parent_account
                d.group_or_ledger='Ledger'
                d.company=company
                d.master_type='Customer'
                d.debit_or_credit='Debit'
                d.is_pl_account='No'
                d.master_name=args['Customer Name']+' - '+args['Id']
                d.freeze_account= "No"
                d.save()

	def validate_po(self,args):
		for k in range(0,len(args)):
			if not (args[k]['Customer Id']).strip():
				return ["Customer Id is not found","error"]
			for j in range(0,len(args[k]['Child'])):
                                        if not ((args[k]['Child'])[j]['Item Name']).strip():
						return ["Item is not found","error"]
					elif not ((args[k]['Child'])[j]['Qty']).strip():
						return ["Quantity is not found","error"]
					elif not (args[k]['Required Date']).strip():
						return ["Required Date is not found","error"]
					else:
						check_id=sql("select name from tabCustomer where innoworth_id='"+(args[k]['Customer Id']).strip()+"'")
                                		if check_id:	
							check_item_name=sql("select name from tabItem where name='"+((args[k]['Child'])[j]['Item Name']).strip()+"'")
							if check_item_name:
								return ["","Done"]
							else:
								return ["Item name is not exist","error"]
                                		else:
							return ["Id is not exist","error"]

	def validate_si(self,s):
			if not (s['Customer Id']).strip():
				return ["Customer Id is not found","error"]
			for r in s['Child']:
				if not (r['Item Name']).strip():
                                	return ["Item is not found","error"]
                                elif not (r['Qty']).strip():
                                        return ["Quantity is not found","error"]
				else:
					check=sql("select name from tabCustomer where innoworth_id='"+(s['Customer Id']).strip()+"'")
					if check:
						return["","Done"]
					else:
						return ["Id is not exist","error"]
 

			
        def validate_customer(self,args):
                for k in range(0,len(args)):
                        if not (args[k]['Id']).strip():
                                return ["Customer Id is not found","error"]
			elif not (args[k]['Customer Name']).strip():
				return ["Customer Name is not found","error"]
			else:
				check_id=sql("select name from tabCustomer where innoworth_id='"+(args[k]['Id']).strip()+"'")
				if check_id:
					return ["Id is already exist","error"]
				else:
					return ["","Done"]


def attach_file(a,path_data):

                #path=self.file_name(path_data[0])
                #html_file= open(path[0],"w")
                import io
                name=path_data[0]
                path=cstr(path_data[0]).replace("/","")
                f = io.open("files/"+path+".html", 'w', encoding='utf8')
                f.write(a)
                f.close()

                s=auth()
                if s[0]=="Done":
			dms_path=webnotes.conn.sql("select value from `tabSingles` where doctype='LDAP Settings' and field='dms_path'",as_list=1)
                        document_attach("files/"+path+".html",dms_path[0][0]+path_data[1]+"/"+path+".html",s[1],"upload")
                        file_attach=Document("File Data")
                        file_attach.file_name="files/"+path+".html"
                        file_attach.attached_to_doctype=path_data[2]
                        file_attach.file_url=dms_path[0][0]+path_data[1]+"/"+path+".html"
                        file_attach.attached_to_name=name
                        file_attach.save()
			os.remove("files/"+path+".html")
                        return s[0]
                else:
                        return s[1]

@webnotes.whitelist()
def add_file():
	data={"Supplier Quotation":"Account","Sales Invoice":"Account","Journal Voucher":"Account"}
	dms_path=webnotes.conn.sql("select value from `tabSingles` where doctype='LDAP Settings' and field='dms_path'",as_list=1)
	name=webnotes.form_dict.get('name')
	source=webnotes.conn.get_value("File Data",name,"file_name")
	file_d=cstr(source).split('/')
	doctype=webnotes.conn.get_value("File Data",name,"attached_to_doctype")
	target=dms_path[0][0]+data[doctype]+"/Kirana/"+file_d[1]
	update=webnotes.conn.sql("update `tabFile Data` set file_url='"+target+"' where name='"+name+"'",debug=1)
	webnotes.conn.commit()
	s=auth()
	if s[0]=="Done":
		document_attach(source,target,s[1],"upload")
		os.remove(source)
		return "Done"
	else:
		return s[1]

@webnotes.whitelist()
def download_file():
	import webbrowser
        source=webnotes.form_dict.get('link')
	s=cstr(source).split('/')
        target="files/download/"
	q=auth()
        if q[0]=="Done":
                document_attach(source,target,q[1],"download")
                return ["File Save Sucessfully",target+'/'+s[len(s)-1]]
        else:
                return q[1]

