// Report Print / PDF dialog customisations.
const DAV_REPORT_PRINT_FORMATS = {
	"Accounts Receivable": "DAV Statement of Account",
};

// Reports that must have a Party selected before printing.
const DAV_REPORTS_REQUIRING_PARTY = ["Accounts Receivable"];

function dav_party_selected(report) {
	const party = report.get_filter_value("party");
	return Array.isArray(party) ? party.length > 0 : !!party;
}

$(document).on("app_ready", function () {
	const original = frappe.ui.get_print_settings;

	frappe.ui.get_print_settings = function () {
		const report = frappe.query_report;
		const report_name = report && report.report_name;

		if (DAV_REPORTS_REQUIRING_PARTY.includes(report_name) && !dav_party_selected(report)) {
			// throw (not return) so the caller does not go on to use a missing dialog
			frappe.throw({
				title: __("Party Required"),
				indicator: "orange",
				message: __("Please select a Party in the filters before printing or downloading the PDF."),
			});
		}

		const dialog = original.apply(this, arguments);
		const print_format = DAV_REPORT_PRINT_FORMATS[report_name];

		if (print_format && dialog && dialog.get_field("print_format")) {
			dialog.set_value("print_format", print_format);
		}
		return dialog;
	};
});
