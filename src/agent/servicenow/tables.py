"""Table names and the fields the agent uses. Keep field lists explicit so leakage filters can reason about them."""
INCIDENT = "incident"
REQUEST = "sc_request"
REQ_ITEM = "sc_req_item"
CATALOG_TASK = "sc_task"
CHANGE = "change_request"
PROBLEM = "problem"
KB = "kb_knowledge"
CI = "cmdb_ci"
CHOICE = "sys_choice"  # choice lists (used by the seeder to match the instance release)

INCIDENT_FIELDS = ["sys_id", "number", "short_description", "description", "category", "subcategory",
                   "impact", "urgency", "priority", "state", "assignment_group", "assigned_to", "cmdb_ci",
                   "sys_created_on", "sys_updated_on", "work_notes", "comments"]
CI_FIELDS = ["sys_id", "name", "sys_class_name", "support_group", "owned_by", "ip_address", "operational_status"]
# Fields that must never be written to a customer-visible channel (Module 12 output filter).
SENSITIVE_CI_FIELDS = {"ip_address", "owned_by", "support_group"}
