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
                        return {"Status":"400","Response":s[0]}
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
                                        message={"Status":"200","Response":"Success"}
                        else:
                                        message={"Status":"400","Response":"Duplicate Customer Name"}
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
					a={"Status":"200","Response":"Success","data":a}
                                else:
                                        a={"Status":200,"Response":"Sales Order Number is not exist"}
			else:
				validate=self.validate_si(i)
				if validate[1]=="error":
	                	        a={"status":"400","Response":validate}
        		        else:
                		        a=self.service_si(i)                		   
                	        	a={"Status":"200","Response":"Success","data":a}
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
		si.charge=webnotes.conn.get_value("Applicable Territory",{"territory":s['Territory']},"parent")
                si.debit_to=webnotes.conn.get_value('Account',{"master_name":si.customer},'name')
                si.price_list_currency='INR'
                si.currency='INR'
                si.selling_price_list='Standard Selling'
                si.fiscal_year=webnotes.conn.get_value("Global Defaults", None, "current_fiscal_year")               
                si.docstatus=1
                si.save()
		html=""
		j=0
		item_list=[]
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
			item_list.append({"item_code":sic.item_code,"export_amt":sic.export_amount})
                        sic.save()
			html+=("<tr><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(j)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.item_code)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.description)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;text-align:right;'><div>"+cstr(sic.qty)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'>"+cstr(sic.stock_uom)+"</td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align:right'>₹ "+cstr(sic.ref_rate)+"</div></td><td style='border:1px solid rgb(153, 153, 153);word-wrap: break-word;'><div style='text-align: right'>₹ "+cstr(sic.export_amount)+"</div></td></tr>")
		tax_total=0.00
		tax_html=""
                if si.charge:
                        tax_total=self.create_tax(si.charge,si.name,item_list,'Sales Invoice','Sales Taxes and Charges',total_amt)
			tax_html=self.sales_tax_html(si.name,None,0)
		si_=Document('Sales Invoice',si.name)
		si_.net_total_export=cstr(total_amt)	
		si_.other_charges_total_export=cstr(tax_total)
                si_.grand_total_export=cstr(flt(si_.net_total_export)+flt(si_.other_charges_total_export))
		si_.grand_total=cstr(si_.grand_total_export)
                si_.rounded_total_export=cstr(round(flt(si_.grand_total_export)))
		adv=c_amt=0.00
		flag=False
                check=0
                total=si_.grand_total_export
                parent_jv=[]
                advance_payment=sql("select credit,parent,name,against_account from `tabJournal Voucher Detail` where account='"+si.debit_to+"' and is_advance='Yes' and credit<>0 and ifnull(against_invoice,'')='' and docstatus=1 order by name asc",as_list=1)
		if advance_payment:
                	for s in advance_payment:
                        	if s[1] not in parent_jv:
                                	parent_jv.append(s[1])
                                if flt(total) < flt(s[0]) and flag==False:
                                	adv=cstr(si_.grand_total_export)
                                        update_jv=sql("update `tabJournal Voucher Detail` set against_invoice='"+si.name+"', credit='"+cstr(total)+"' where name='"+s[2]+"'")
                                        jv = Document("Journal Voucher Detail")
                                        jv.account=si.debit_to
                                        jv.cost_center= "Main - Frsh"
                                        jv.credit= cstr(flt(s[0])-flt(total))
                                        jv.is_advance= "Yes"
                                        jv.parent=s[1]
                                        jv.against_account=s[3]
                                        jv.docstatus=1
                                        jv.save()
                                        flag=True
                                elif flag==False:
                                	adv=cstr(flt(adv)+flt(s[0]))
                                        total=cstr(flt(total)-flt(s[0]))
                                        update_jv=sql("update `tabJournal Voucher Detail` set against_invoice='"+si.name+"' where name='"+s[2]+"'")
                                        if flt(total)==0:
                                        	flag=True
                                        else:
                                        	flag=False
		si_.total_advance=cstr(adv)
		si_.outstanding_amount=cstr(flt(si_.grand_total_export)-flt(adv))
                si_.docstatus=1
		si_.save()
		if parent_jv:
                	self.make_adv_payment_gl(parent_jv)
                data=[{"against_voucher":si.name,"account":si.debit_to,"debit":cstr(si_.grand_total_export),"credit":"0","against":"Sales - innow","against_voucher_type":"Sales Invoice","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":""},{"against_voucher":"","account":'Sales - innow',"debit":"0","credit":cstr(total_amt),"against":si.debit_to,"against_voucher_type":"","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":"Main - innow"}]
                self.create_gl(data)
		
		a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"customer_name":si.customer_name,"net_total":si_.net_total_export,"grand_total":si_.grand_total_export,"rounded_total":si_.rounded_total_export,"table_data":html,"date_1":"Posting Date","date_2":"Due Date","doctype":"Sales Invoice","doctype_no":si.name,"company":si.company,"addr_name":"","address":"","tax_detail":tax_html})
                file_path_=attach_file(a,[si.name,"Account/Kirana","Sales Invoice"])
                return {"Sales Invoice":si.name,"File Copy":file_path_}


	def make_si(self,args):
			parent=sql("select * from `tabSales Order` where name='"+(args['Sales Order No']).strip()+"'",as_dict=1)
			if parent:
				for r in parent:
					si=Document("Sales Invoice")
					si.customer=r['customer']
					si.customer_name=r['customer_name']
					si.posting_date=nowdate()
					si.due_date=nowdate()
					si.charge=r['charge']
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
					si.other_charges_total_export=cstr(r['other_charges_total_export'])
					si.grand_total=cstr(r['grand_total_export'])
                        		si.rounded_total_export=cstr(r['rounded_total_export'])
					si.save()
					si=Document("Sales Invoice",si.name)
					adv=c_amt=0.00
					flag=False
					check=0
					total=si.grand_total_export
					parent_jv=[]
					advance_payment=sql("select credit,parent,name,against_account from `tabJournal Voucher Detail` where account='"+si.debit_to+"' and is_advance='Yes' and credit<>0 and ifnull(against_invoice,'')='' and docstatus=1 order by name asc",as_list=1)
                			if advance_payment:
                        			for s in advance_payment:
							if s[1] not in parent_jv:
								parent_jv.append(s[1])
							if flt(total) < flt(s[0]) and flag==False:
								adv=cstr(si.grand_total_export)
								update_jv=sql("update `tabJournal Voucher Detail` set against_invoice='"+si.name+"', credit='"+cstr(total)+"' where name='"+s[2]+"'")
								jv = Document("Journal Voucher Detail")
           							jv.account=si.debit_to
           							jv.cost_center= "Main - Frsh"
       								jv.credit= cstr(flt(s[0])-flt(total))
           							jv.is_advance= "Yes"
           							jv.parent=s[1]
								jv.against_account=s[3]
								jv.docstatus=1
								jv.save()
								flag=True
							elif flag==False:
								adv=cstr(flt(adv)+flt(s[0]))
								total=cstr(flt(total)-flt(s[0]))
								update_jv=sql("update `tabJournal Voucher Detail` set against_invoice='"+si.name+"' where name='"+s[2]+"'")
								if flt(total)==0:
									flag=True
								else:
									flag=False
					si.total_advance=cstr(adv)
					si.outstanding_amount=cstr(flt(r['grand_total_export'])-flt(adv))
					si.docstatus=1	
					si.save()
					update=sql("update `tabSales Order` set per_billed='100' where name='"+cstr(r['name'])+"'")
					child=sql("select * from `tabSales Order Item` where parent='"+(args['Sales Order No']).strip()+"'",as_dict=1)
					html=""
					j=0
					credit_amt=0.00
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
						c_amt=cstr(flt(c_amt)+flt(sic.amount))
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
					
					tax_html=self.sales_tax_html((args['Sales Order No']).strip(),si.name,1)
					if parent_jv:
						self.make_adv_payment_gl(parent_jv)
					data=[{"against_voucher":si.name,"account":si.debit_to,"debit":cstr(si.grand_total_export),"credit":"0","against":"Sales - innow","against_voucher_type":"Sales Invoice","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":""},{"account":'Sales - innow',"debit":"0","credit":cstr(c_amt),"against":si.debit_to,"against_voucher_type":"","voucher_type":"Sales Invoice","voucher_no":si.name,"cost_center":"Main - innow","against_voucher":""}]

					self.create_gl(data)

					a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"customer_name":si.customer_name,"net_total":cstr(si.net_total_export),"grand_total":cstr(si.grand_total_export),"rounded_total":cstr(si.rounded_total_export),"table_data":html,"date_1":"Posting Date","date_2":"Due Date","doctype":"Sales Invoice","doctype_no":si.name,"company":si.company,"addr_name":"","address":"","tax_detail":tax_html})

                        		file_path_=attach_file(a,[si.name,"Account/Kirana","Sales Invoice"])
					return {"Sales Invoice":si.namek,"File Copy":file_path_}

	def sales_tax_html(self,parent,name,c):
		tax_html=''
		gl_data=[]
		voucher_no=name
		tax_data=sql("select charge_type,account_head,rate,description,tax_amount,total,parenttype,row_id from `tabSales Taxes and Charges` where parent='"+parent+"'",as_dict=1)
		if tax_data:
                	for tax in tax_data:
				if cint(c)==1:
					t=Document('Sales Taxes and Charges')
                        		t.parent=name
                        		t.account_head=tax['account_head']
                        		t.parentfield="other_charges"
                        		t.charge_type=tax['charge_type']
                        		t.description=tax['description']
                        		t.row_id=tax['row_id']
                        		t.docstatus=1
                        		t.parenttype='Sales Invoice'
					t.rate=tax['rate']
					t.tax_amount=tax['tax_amount']
					t.total=tax['total']
					t.save()
                		tax_html+=("<tr><td style='width:50%;'>"+tax['description']+"</td><td style='width:50%;text-align:right;'>₹ "+cstr(tax['tax_amount'])+"</td></tr>")
				if name==None:
					voucher_no=parent
				gl_data.append({
                                	"account":tax['account_head'],
                                        "cost_center":'Main - Frsh',
                                        "debit":0,
                                        "credit":cstr(tax['tax_amount']),
                                        "against":webnotes.conn.get_value('Sales Invoice',voucher_no,'debit_to'),
                                        "against_voucher":"",
                                        "against_voucher_type":"",
                                        "voucher_type":"Sales Invoice",
                                        "voucher_no":voucher_no
                                })
			self.create_gl(gl_data)	
			return tax_html 

	def make_adv_payment_gl(self,jv):
		gl_data=[]
		for s in jv:
			delete_gl=sql("delete from `tabGL Entry` where voucher_no=%s",s)
			jv_data=sql("select name,account,cost_center,debit,credit,against_invoice,against_account,parent from `tabJournal Voucher Detail` where parent=%s",s,as_dict=1)
			if jv_data:
				for j in jv_data:
					gl_data.append({
						"account":j['account'],
						"cost_center":j['cost_center'],
						"debit":j['debit'],
						"credit":j['credit'],
						"against":j['against_account'],
						"against_voucher":j['against_invoice'],
						"against_voucher_type":"Sales Invoice",
						"voucher_type":"Journal Voucher",
						"voucher_no":j['parent']
					})
		self.create_gl(gl_data) 

	def create_gl(self,data):
		for r in data:
			gl=Document("GL Entry")
			gl.account=r['account']
			gl.debit=r['debit']
			gl.credit=r['credit']
			gl.against=r['against']
			gl.against_voucher_type=r['against_voucher_type']
			gl.voucher_type=r['voucher_type']
			gl.against_voucher=r['against_voucher']
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
			return {"Status":"400","Response":s[0]}
		else:
			for r in args:	
				po=self.make_po(r)
				so=self.make_so(r)
			return {"Status":"200","Response":"Success","data":so}

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
			so.charge=webnotes.conn.get_value("Applicable Territory",{"territory":so.territory},"parent")
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
		item_list=[]
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
                                item_list.append({"item_code":soi.item_code,"export_amt":soi.export_amount})
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
		tax_total=0.00
		if so.charge:
			tax_total=self.create_tax(so.charge,so.name,item_list,'Sales Order','Sales Taxes and Charges',net_tot)
                so_=Document("Sales Order",so.name)
                so_.net_total_export=net_tot	
		so_.other_charges_total_export=cstr(tax_total)
                so_.grand_total_export=cstr(flt(so_.net_total_export)+flt(so_.other_charges_total_export))
                so_.rounded_total_export=cstr(round(flt(so_.grand_total_export)))
                so_.save()
                a=html_data({"posting_date":datetime.datetime.strptime(nowdate(),'%Y-%m-%d').strftime('%d/%m/%Y'),"due_date":datetime.datetime.strptime(so.delivery_date,'%Y-%m-%d').strftime('%d/%m/%Y'),"customer_name":so.customer_name,"net_total":net_tot,"grand_total":net_tot,"rounded_total":net_tot,"table_data":html,"date_1":"Sales Order Date","date_2":"Expected Delivery Date","doctype":"Sales Order","doctype_no":so.name,"company":so.company,"addr_name":"Customer Address","address":so.address_display,"tax_detail":""})
                file_path_=attach_file(a,[so.name,"Selling/Kirana","Sales Order"])
                return {"Sales Order":so.name,"File Copy":file_path_}
		
	def create_tax(self,master,parent,item_list,parenttype,tax_table,net_total):
			row=0
			total_amt_=final_amt=0.00
			row_amt=[]
			test_dict = {}
			tax=sql("select * from `tab"+tax_table+"` where parent='"+master+"'",as_dict=1)
			for s in tax:
				t=Document(tax_table)
				t.parent=parent
				t.account_head=s['account_head']
				t.parentfield="other_charges"
				t.charge_type=s['charge_type']
				t.description=s['description']
				t.row_id=s['row_id']
				t.docstatus=1
				t.parenttype=parenttype
				actual=0
				amt=0.00
				row=row+1
				test_dict.setdefault(row,{})
				for item in item_list:
					t.rate=webnotes.conn.get_value("Item Tax",{"parent":item['item_code'],"tax_type":s['account_head']},"tax_rate")
					if not t.rate:
						t.rate=s['rate']
					if t.charge_type=="On Net Total":
						amt=cstr(flt(amt)+flt(flt(item['export_amt'])*flt(t.rate)/100))
						net_total=cstr(flt(net_total)+flt(flt(item['export_amt'])*flt(t.rate)/100))
						total_amt_=cstr(flt(flt(item['export_amt'])*flt(t.rate)/100)+flt(item['export_amt']))
						test_dict[row].setdefault(item['item_code'],{})
						test_dict[row][item['item_code']]['amount']= cstr(flt(item['export_amt'])*flt(t.rate)/100)
						test_dict[row][item['item_code']]['total']=cstr(total_amt_)

					elif t.charge_type=="On Previous Row Amount":
						for rowid in test_dict:
							if cint(rowid)==cint(s['row_id']):
								for dict_item in test_dict[rowid]:
									if dict_item==item['item_code']:
										prev_amt=cstr(test_dict[rowid][dict_item]['amount'])
										amt=cstr(flt(amt)+flt(flt(prev_amt)*flt(t.rate)/100))
                                                				net_total=cstr(flt(net_total)+flt(flt(prev_amt)*flt(t.rate)/100))
										total_amt_=cstr(flt(flt(prev_amt)*flt(t.rate)/100)+flt(item['export_amt']))
                                                				test_dict[row].setdefault(item['item_code'],{})
                                                				test_dict[row][item['item_code']]['amount']= cstr(flt(prev_amt)*flt(t.rate)/100)
                                                				test_dict[row][item['item_code']]['total']=cstr(total_amt_)

					elif t.charge_type=="On Previous Row Total":
						for rowid in test_dict:
                                                	if cint(rowid)==cint(s['row_id']):
                                                                for dict_item in test_dict[rowid]:
									if dict_item==item['item_code']:
										prev_total=cstr(test_dict[rowid][dict_item]['total'])
                                                                		amt=cstr(flt(amt)+flt(flt(prev_total)*flt(t.rate)/100))
                                                                		net_total=cstr(flt(net_total)+flt(flt(prev_total)*flt(t.rate)/100))
										total_amt_=cstr(flt(flt(prev_total)*flt(t.rate)/100)+flt(item['export_amt']))
										test_dict[row].setdefault(item['item_code'],{})
                                                                        	test_dict[row][item['item_code']]['amount']= cstr(flt(prev_total)*flt(t.rate)/100)
                                                                        	test_dict[row][item['item_code']]['total']=cstr(total_amt_)
					elif t.charge_type=="Actual":
						if cint(actual)==0:
							actual=actual+1
                                                	amt=cstr(flt(amt)+flt(t.rate))
							net_total=cstr(flt(net_total)+flt(amt))
							test_dict[row].setdefault(item['item_code'],{})
                                                        test_dict[row][item['item_code']]['amount']= cstr(amt)
                                                        test_dict[row][item['item_code']]['total']=cstr(net_total)
				final_amt=cstr(flt(final_amt)+flt(amt))	
				t.tax_amount=cstr(amt)
				t.total=cstr(net_total)
				t.save()
			return final_amt

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
				return ["Customer id is missing.","error"]
			for j in range(0,len(args[k]['Child'])):
                                        if not ((args[k]['Child'])[j]['Item Name']).strip():
						return ["Item is missing.","error"]
					elif not ((args[k]['Child'])[j]['Qty']).strip():
						return ["Quantity is missing.","error"]
					elif not (args[k]['Required Date']).strip():
						return ["Required date is missing.","error"]
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
				return ["Customer id is missing.","error"]
			for r in s['Child']:
				if not (r['Item Name']).strip():
                                	return ["Item is missing.","error"]
                                elif not (r['Qty']).strip():
                                        return ["Quantity is missing.","error"]
				else:
					check=sql("select name from tabCustomer where innoworth_id='"+(s['Customer Id']).strip()+"'")
					if check:
						check_item_name=sql("select name from tabItem where name='"+(r['Item Name']).strip()+"'")
                                                if check_item_name:
                                                	return ["","Done"]
                                                else:
                                                	return ["Item name is not exist","error"]
					else:
						return ["Id is not exist","error"]
 

			
        def validate_customer(self,args):
                for k in range(0,len(args)):
                        if not (args[k]['Id']).strip():
                                return ["Customer ID is missing","error"]
			elif not (args[k]['Customer Name']).strip():
				return ["Customer Name is missing.","error"]
			else:
				check_id=sql("select name from tabCustomer where innoworth_id='"+(args[k]['Id']).strip()+"'")
				if check_id:
					return ["Duplicate customer id.","error"]
				else:
					return ["","Done"]


@webnotes.whitelist()
def attach_file(a,path_data):
		import easywebdav
                #path=self.file_name(path_data[0])
                #html_file= open(path[0],"w")
                import io
		html_=a
                name=path_data[0]
                path=cstr(path_data[0]).replace("/","")
                f = io.open("files/"+path+".html", 'w', encoding='utf8')
                f.write(a)
                f.close()
                s=auth()
                if s[0]=="Done":
			path_name=create_path(nowdate(),path_data[1],s[1])
			check_status=sql("select file_url from `tabFile Data` where file_url='"+path_name+"/"+path+".html"+"'",as_list=1)
			if not check_status:
                        	document_attach("files/"+path+".html",path_name+"/"+path+".html",s[1],"upload")
                        	file_attach=Document("File Data")
                        	file_attach.file_name="files/"+path+".html"
                        	file_attach.attached_to_doctype=path_data[2]
                        	file_attach.file_url=path_name+"/"+path+".html"
                        	file_attach.attached_to_name=name
                        	file_attach.save()
				os.remove("files/"+path+".html")
                        	return path_name+"/"+path+".html"
			else:
				return "File Already Exist"
                else:
                        return s[1]

@webnotes.whitelist()
def create_path(date,path_data,auth_id):
	dms_path=webnotes.conn.sql("select value from `tabSingles` where doctype='LDAP Settings' and field='dms_path'",as_list=1)
	check_path=webnotes.conn.sql("select name from tabPath where name='"+dms_path[0][0]+path_data+"/"+date+"'",as_list=1)
	if check_path:
		return check_path[0][0]
	else:
		p=Document('Path')
		p.path=cstr(dms_path[0][0]+path_data+"/"+date)
		p.save()
		auth_id.mkdir(dms_path[0][0]+path_data+"/"+date)
		return p.name

@webnotes.whitelist()
def add_file():
	data={"Supplier Quotation":"Account","Sales Invoice":"Account","Journal Voucher":"Account"}
	dms_path=webnotes.conn.sql("select value from `tabSingles` where doctype='LDAP Settings' and field='dms_path'",as_list=1)
	name=webnotes.form_dict.get('name')
	source=webnotes.conn.get_value("File Data",name,"file_name")
	file_d=cstr(source).split('/')
	doctype=webnotes.conn.get_value("File Data",name,"attached_to_doctype")
	target=dms_path[0][0]+data[doctype]+"/Kirana/"+file_d[1]
	update=webnotes.conn.sql("update `tabFile Data` set file_url='"+target+"' where name='"+name+"'")
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
	import pdfkit
	import os
	import urlparse, urllib
        source=webnotes.form_dict.get('link')
	s=cstr(source).split('/')
        target="files/download/"
	q=auth()
        if q[0]=="Done":
                document_attach(source,target,q[1],"download")
		'''
		url=os.path.abspath(target+'/'+s[len(s)-1])
		target_pdf=os.path.abspath('/home/gangadhar/test.pdf')
		url=urlparse.urljoin('file:', urllib.pathname2url(url))
		webnotes.errprint([url,target_pdf])
		pdfkit.from_url(url,urlparse.urljoin('file:', urllib.pathname2url(target_pdf)))
		'''
                return ["File Save Sucessfully",target+'/'+s[len(s)-1]]
        else:
                return q[1]

