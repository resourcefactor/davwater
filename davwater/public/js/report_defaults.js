// Pre-select the default print format in the report Print / PDF dialog.
const DAV_REPORT_PRINT_FORMATS = {
	"Accounts Receivable": "DAV Statement of Account",
};

$(document).on("app_ready", function () {
	const original = frappe.ui.get_print_settings;

	frappe.ui.get_print_settings = function () {
		const dialog = original.apply(this, arguments);
		const report_name = frappe.query_report && frappe.query_report.report_name;
		const print_format = DAV_REPORT_PRINT_FORMATS[report_name];

		if (print_format && dialog && dialog.get_field("print_format")) {
			dialog.set_value("print_format", print_format);
		}
		return dialog;
	};
});
