from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from stock.utils import get_buying_amount
from webnotes import _, msgprint
sql = webnotes.conn.sql

def execute(filters=None):
	if not filters: filters = {}
        #user=webnotes.session['user']
        #msgprint("hi "+user)
	query = "select t1.item_code,t2.item_code,t1.0d1,t1.0d2,t1.l2,t1.l1,t1.uncoated,t1.tiain_coated,t1.fm_star,t1.helix_angle,t1.series,t1.item_group,t1.brand from tabItem  t2 join tabItem t1 on t1.0d1=t2.0d1 and t1.0d2=t2.0d2 and t1.l2=t2.l2 and t1.l1= t2.l1 and t1.item_code<> t2.item_code where t1.design_feature='2 Flute'"
        #msgprint(query)      
	res=sql(query)
	columns = ["2 Flute::120", "4 Flute::120","0d1 (h10):int:70","0d2(h6):int:70","L2:int:60","L1:int:60","Uncoated:Check:60","TiAIN Coated:Check:70","Star:Data:120","Helix Angle:Data:80","Series:Data:130","Item Group:Data:100","Brand:Data:100"]
				
	return columns, res

