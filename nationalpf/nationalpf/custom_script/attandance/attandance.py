
import frappe
from datetime import datetime, timedelta,timezone
from frappe.utils import get_first_day, get_last_day, date_diff,time_diff_in_hours
from datetime import timedelta

# from datetime import datetime, timezone


# @frappe.whitelist()
def get_attendance(doc,method):
	try:
		row_data = doc.as_dict()

		if isinstance(row_data.get("time"),str):
			convert_str = row_data.get("time")
			convert_str = datetime.strptime(row_data.get("time"), "%Y-%m-%d %H:%M:%S")
			checkin_date = convert_str.date()
		else:
			convert_str = row_data.get("time")
			checkin_date = convert_str.date()
		
	   
		if row_data.get("log_type") == "IN":
			if not frappe.db.exists("Attendance",{"employee":row_data.get("employee"),"attendance_date":checkin_date}):
			# Create a new attendance record if an "IN" log is received
				attendance_id = create_attendance_record(row_data, checkin_date)
				update_attendance_in_checkins([row_data.get("name")], attendance_id)
			else:
				# if already creating attendance of that day
				attendance_doc = frappe.get_doc("Attendance",{"employee":row_data.get("employee"),"attendance_date":checkin_date})
				attendance_id_in = attendance_doc.name
				update_attendance_in_checkins([row_data.get("name")], attendance_id_in)
		

		
		if row_data.get("log_type") == "OUT":
			# If an "OUT" log is received, update the latest attendance record that has no "OUT" time
			if frappe.db.exists("Attendance",{"employee":row_data.get("employee"),"attendance_date":checkin_date}):
				attendance_doc = frappe.get_doc("Attendance",{"employee":row_data.get("employee"),"attendance_date":checkin_date})
				if attendance_doc.status != "On Leave":
					if attendance_doc.docstatus == 1:
						frappe.db.set_value("Attendance", attendance_doc.name,{"out_time": row_data.get("time")})
						frappe.db.commit()
						attendance_id_out = attendance_doc.name
						update_attendance_in_checkins([row_data.get("name")], attendance_id_out)
						calculate_total_hours(attendance_id_out,row_data.get("time"))
					else:
						attendance_doc.out_time = row_data.get("time")
						attendance_doc.save(ignore_permissions=True)
						frappe.db.commit()
						attendance_id_out = attendance_doc.name
						update_attendance_in_checkins([row_data.get("name")], attendance_id_out)
						calculate_total_hours(attendance_id_out,row_data.get("time"))
				else:
					get_checkout_present_or_previou(row_data,checkin_date)
			else:
				get_checkout_present_or_previou(row_data,checkin_date)
				
					
	except Exception as e:
		frappe.log_error("get_attendance",str(e))

def get_checkout_present_or_previou(row_data,checkin_date):         
		previou_day = checkin_date - timedelta(1)
		attendance_prev_id = frappe.get_doc("Attendance",{"employee":row_data.get("employee"),"attendance_date":previou_day})
		if attendance_prev_id.docstatus == 1:
			frappe.db.set_value("Attendance", attendance_prev_id.name,{"out_time": row_data.get("time")})
			frappe.db.commit()
			attendance_id_out = attendance_prev_id.name
			update_attendance_in_checkins([row_data.get("name")], attendance_id_out)
			calculate_total_hours(attendance_id_out,previou_day,)

		else:
			attendance_prev_id.out_time = row_data.get("time")
			attendance_prev_id.save(ignore_permissions=True)
			frappe.db.commit()
			attendance_id_pre = attendance_prev_id.name
			update_attendance_in_checkins([row_data.get("name")],attendance_id_pre)
			calculate_total_hours(attendance_id_pre,previou_day)

def create_attendance_record(row_data, checkin_date):
	attendance_doc = {
		"doctype": "Attendance",
		"employee": row_data.get("employee"),
		"attendance_date": checkin_date,
		"shift": row_data.get("shift"),
		"status":"Present",
		"in_time": row_data.get("time") if row_data.get("log_type") == "IN" else None
	}
	new_attendance = frappe.get_doc(attendance_doc)
	new_attendance.insert(ignore_permissions=True)
	return new_attendance.name

def update_attendance_in_checkins(log_names: list, attendance_id: str):
	checkin_doc = frappe.get_doc("Employee Checkin", {"name":log_names[0]})
	checkin_doc.attendance =attendance_id
	checkin_doc.flags.ignore_validate = True
	checkin_doc.save(ignore_permissions=True)
	frappe.db.commit()

	check_in_list = frappe.db.get_list("Employee Checkin", {"attendance":attendance_id}, [ "time"],order_by="time")
	in_time = check_in_list[0].time
	out_time = check_in_list[-1].time


def calculate_total_hours(attendance_doc, checkin_date):
	
	attendance_id = frappe.get_doc("Attendance", {"name": attendance_doc})
	query = """
		SELECT name, log_type, time 
		FROM `tabEmployee Checkin` 
		WHERE attendance = %s 
		ORDER BY time ASC;
	"""
	totalemp_checkins = frappe.db.sql(query, (attendance_doc,), as_dict=True)

	total_hour = 0
	intime_hours = None
	inout_hours = None
	is_lastout = True
	if len(totalemp_checkins) >= 2:
		for each in totalemp_checkins:
			if each.get("log_type") == "IN":
				intime_hours = each.get("time")

			if each.get("log_type") == "OUT":
				inout_hours = each.get("time")
				is_lastout = False

			if intime_hours and inout_hours:
		
				# if intime_hours < inout_hours:
				in_time = intime_hours
				out_time = inout_hours
				total_hour += abs(round((out_time - in_time).total_seconds() / 3600.0,2))
				intime_hours = None
				inout_hours = None

	else:
		if attendance_id.in_time and attendance_id.out_time:
			in_time = attendance_id.in_time
			out_time = attendance_id.out_time
			total_hour = abs(round((out_time - in_time).total_seconds() / 3600.0,2))
	

	if attendance_id.docstatus == 1:
		frappe.db.set_value("Attendance", attendance_id.name,{"working_hours":total_hour})
		frappe.db.commit()

	
	if total_hour >= 6:
		if attendance_id.docstatus == 1:
			pass
		else:
			attendance_id.working_hours = total_hour
			attendance_id.save(ignore_permissions=True)
			attendance_id.submit()
			frappe.db.commit()
	
	else:
		attendance_id.working_hours = total_hour   
		attendance_id.save(ignore_permissions=True)
		frappe.db.commit()
  





@frappe.whitelist()
def get_ot_hours_pay(self, method = None):

	try:					
		# self = frappe.get_doc("Salary Slip",self)
		employee_doc = frappe.get_doc("Employee", self.employee)

		if not employee_doc:
			frappe.throw("Employee details not found.")

		if not employee_doc.holiday_list:
			frappe.throw("Designation not found.")

		attendance_records = frappe.get_all("Attendance", filters={
			"employee": employee_doc.name,
			"attendance_date": ["Between", [self.start_date, self.end_date]]
		}, fields=['*'])

		if not attendance_records:
			frappe.throw("Attendance details not found.")
			return

		shift_type_doc = frappe.get_doc("Shift Type", employee_doc.default_shift)
		if not shift_type_doc:
			frappe.throw("Shift type not found in employee details.")
			return

		if employee_doc.custom_ot_eligibility == "Yes":
			start_time = shift_type_doc.start_time
			end_time = shift_type_doc.end_time
			tome_dur = end_time - start_time
			working_hours_total = 0
			ot_hours_total = 0
			holiday_list_doc = frappe.get_doc("Holiday List", employee_doc.holiday_list)



			first_day = get_first_day(self.start_date)
			last_day = get_last_day(self.start_date)
			total_days_in_month = date_diff(last_day, first_day) + 1
			holidays_in_month = [
				holiday.holiday_date
				for holiday in holiday_list_doc.holidays
				if first_day <= holiday.holiday_date <= last_day
			]
			total_days_in_month -= len(holidays_in_month)


			overlapping_attendance = [
				att["attendance_date"] for att in attendance_records
				if att["attendance_date"] in holidays_in_month
			]
			present_count = sum(1 for att in attendance_records if att["status"] == "Present")
			medical_leave_records = [
				att for att in attendance_records
				if att["status"] == "On Leave" and att.get("leave_type") == "Medical Leave"
			]
			medical_leave_count = len(medical_leave_records)
			total_present_and_medical_leave = present_count + medical_leave_count

			insetive_hour = 0
			for record in attendance_records:
				working_time = timedelta(hours=round(record.working_hours))
				if record.attendance_date not in [holiday.holiday_date for holiday in holiday_list_doc.holidays]:
					# insetive_hour+= 3
					ot_hours_total += round(record.working_hours) - abs(round(tome_dur.total_seconds() / 3600.0, 2))
					
					if round(record.working_hours) > round(tome_dur.total_seconds() / 3600.0, 2):
						insetive_hour += 3

			if not holiday_list_doc:
				frappe.throw("Holiday List not found in employee details.")

			base_amount = 0
			insentve_basic = 0
			if employee_doc.custom_ot_formula == "NOT" or employee_doc.custom_ot_formula == "BF/360":
				
	   
				base_amount = sum(
					next((amount.amount for amount in employee_doc.custom_earnings if amount.salary_component == component), 0)
					for component in ["Basic Pay", "Food Allowance"]
				)
			

			if employee_doc.custom_ot_formula == "B/240" or employee_doc.custom_ot_formula == "B/300":
				base_amount = next((amount.amount for amount in employee_doc.custom_earnings if amount.salary_component == "Basic Pay"), 0)
				
			

			

			if employee_doc.custom_ot_formula == "NOT" or employee_doc.custom_ot_formula == "B/240":
				if total_present_and_medical_leave >= total_days_in_month or len(overlapping_attendance)>2:
						attadance =get_employee_addision_salary(self)
				insentve_basic = base_amount /240
				base_amount = base_amount / 240
			if employee_doc.custom_ot_formula == "BF/360":
				insentve_basic = base_amount /360
				base_amount = base_amount / 360
			if employee_doc.custom_ot_formula == "B/300":
				insentve_basic = base_amount /300
				base_amount = base_amount / 300
		
			
			calculate_ot_amount = 0
			actuval_amount = 0
			if employee_doc.custom_ot_formula == "B/300" or employee_doc.custom_ot_formula == "BF/360":
				
				calculate_ot_amount += base_amount * ot_hours_total
				actuval_amount = insentve_basic * insetive_hour 

			else:
				actuval_amount = insentve_basic * insetive_hour * 1.25
				calculate_ot_amount += base_amount *  1.25 * ot_hours_total


			week_off_working = 0
			insentve_basic_amount = 0
			working_ot_hour_in_holidays = 0
			for record in attendance_records:
				if record.attendance_date  in [holiday.holiday_date for holiday in holiday_list_doc.holidays]:
				
					working_hours_total += record.working_hours
					week_off_working += record.working_hours 
					if employee_doc.custom_ot_formula == "B/300" or employee_doc.custom_ot_formula == "BF/360":
						insentve_basic_amount = insentve_basic * week_off_working
						working_ot_hour_in_holidays = base_amount * (working_hours_total )
					else:
						insentve_basic_amount = insentve_basic * week_off_working * 1.5
						working_ot_hour_in_holidays = base_amount * 1.5  * (working_hours_total )
		
			insentve_basic_total_amount = insentve_basic_amount + actuval_amount if calculate_ot_amount != 0 else insentve_basic_amount
			amount = insentve_basic_total_amount - calculate_ot_amount -working_ot_hour_in_holidays
			# return working_ot_hour_in_holidays
			# return base_amount * (working_hours_total ) *1.5
			incentive_amount_funt = incentive_amount(self,amount)
			self.custom_ot_hour = (working_hours_total + ot_hours_total)
			self.custom_ot_pay_amount = calculate_ot_amount + working_ot_hour_in_holidays

			current_year = datetime.now().year
			current_month = datetime.now().month
			date_25th = datetime(current_year, current_month, 25)

			formatted_date = date_25th.strftime("%Y-%m-%d")
			
			new_additional_salary = frappe.new_doc("Additional Salary")
			new_additional_salary.update({
				"employee": self.employee,
				"company": self.company,
				"payroll_date": "2024-11-25",# formatted_date,
				"salary_component": "OT Arrears",
				"currency": "AED",	
				"amount": self.custom_ot_pay_amount,
				"docstatus": 1
			})
			new_additional_salary.insert(ignore_permissions=True)

			frappe.db.commit()
		
	except Exception as ex:
		frappe.log_error(message=str(ex), title="Error in OT Calculation")
		return str(ex)
	




@frappe.whitelist()
def get_employee_addision_salary(self):
	try:
		current_year = datetime.now().year
		current_month = datetime.now().month
		date_25th = datetime(current_year, current_month, 25)

		formatted_date = date_25th.strftime("%Y-%m-%d")
		add_addisnal_salary = frappe.new_doc("Additional Salary")
		add_addisnal_salary.update({
			"employee": self.employee,
			"company": self.company,
			"payroll_date": "2024-11-25",# formatted_date,
			"salary_component": "Attendance Allowance",
			"currency": "AED",	
			"amount": 100,
			"docstatus": 1
		})
		add_addisnal_salary.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as ex:
		frappe.log_error(message=str(ex), title="Error in Employee Details")
		return str(ex)





@frappe.whitelist()
def incentive_amount(self,amount):
	try:
		current_year = datetime.now().year
		current_month = datetime.now().month
		date_25th = datetime(current_year, current_month, 25)

		formatted_date = date_25th.strftime("%Y-%m-%d")
		add_addisnal_salary = frappe.new_doc("Additional Salary")
		add_addisnal_salary.update({
			"employee": self.employee,
			"company": self.company,
			"payroll_date": "2024-11-25",# formatted_date,
			"salary_component": "Incentive",
			"currency": "AED",	
			"amount": amount,
			"docstatus": 1
		})
		add_addisnal_salary.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as ex:
		frappe.log_error(message=str(ex), title="Error in Employee Details")
		return str(ex)