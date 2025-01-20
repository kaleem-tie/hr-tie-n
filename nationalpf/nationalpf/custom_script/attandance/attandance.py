
import frappe
from datetime import datetime, timedelta,timezone

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
def get_ot_hours_pay(self, method):
	try:
		employe_base_amount = frappe.get_doc("Employee", self.employee)

		if not employe_base_amount:
			frappe.throw("Employee details not found.")

		attan = frappe.get_all("Attendance", filters={"employee": employe_base_amount.name, "attendance_date": ["Between", [self.start_date, self.end_date]]}, fields=['*'])
		if not attan:
			frappe.throw("Attendance details not found.")
			
		docu = frappe.get_doc("Shift Type", attan[0].shift)

		if not docu:
			frappe.error_log("Shift type not found.")
			return
		if employe_base_amount.custom_ot_eligibility == "Yes":
			start_time = docu.start_time
			end_time = docu.end_time
			working = 0

			tome_dur = end_time - start_time
			working_hours = 0
			ot_hours = 0
			for i in attan:
				working_hours += round(i.working_hours)

				if i.working_hours - abs(round(tome_dur.total_seconds() / 3600.0, 2)) <= 3:
					ot_hours += round(i.working_hours) - abs(round(tome_dur.total_seconds() / 3600.0, 2))
				if i.working_hours - abs(round(tome_dur.total_seconds() / 3600.0, 2)) > 3:
					ot_hours += 3

			holida_list = frappe.get_doc("Holiday List", docu.holiday_list)
			if not holida_list:
				frappe.throw("Holiday List not found.")

			base_amount = next((amount.amount for amount in employe_base_amount.custom_earnings if amount.salary_component == "Basic Pay"),0)  # Default to 0 if no match is found

			# base_amount = employe_base_amount.custom_gross_amount


			calculate_ot_amount = 0
			per_hour_amount = base_amount / 30 / abs(round(tome_dur.total_seconds() / 3600.0, 2))
			
			calculate_ot_amount += round(per_hour_amount) * 1.25 * ot_hours
			
			for j in attan:
				if any(j.attendance_date == holiday.holiday_date for holiday in holida_list.holidays):
					working += j.working_hours

					if abs(round(tome_dur.total_seconds() / 3600.0, 2)) <= 12:
						calculate_ot_amount = round(per_hour_amount) * 1.5 * working
					if abs(round(tome_dur.total_seconds() / 3600.0, 2)) > 12:
						calculate_ot_amount = round(per_hour_amount) * 1.5 * 12

			self.custom_ot_hour = round(working + ot_hours)
			self.custom_ot_pay_amount = round(calculate_ot_amount)

			frappe.db.commit()

		current_year = datetime.now().year
		current_month = datetime.now().month

		date_25th = datetime(current_year, current_month, 25)

		formatted_date = date_25th.strftime("%Y-%m-%d")
		new_additional_salary = frappe.new_doc("Additional Salary")
		new_additional_salary.update({
			"employee":self.employee,
			"company":self.company,
			"payroll_date":'2024-11-25',#formatted_date
			"salary_component":"OT Arrears",
			"currency":"AED",
			"amount": round(calculate_ot_amount),
			"docstatus":1

		})
		new_additional_salary.insert()
		frappe.db.commit()
	except Exception as ex:
		return str(ex)