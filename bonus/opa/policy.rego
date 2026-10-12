package lab24.authz

import rego.v1

default allow := false

allow if count(deny_reasons) == 0

deny_reasons contains "restricted data cannot leave through egress" if {
	input.data_classification == "restricted"
	input.egress_enabled == true
}

deny_reasons contains "unknown data classification" if {
	not input.data_classification in {"public", "internal", "restricted"}
}

deny_reasons contains "missing agent identity" if not input.agent_owner

deny_reasons contains "invalid delegation depth" if input.delegation_depth < 0

principal := object.get(data.principals, input.principal_id, {})

deny_reasons contains "unknown principal" if {
	count(principal) == 0
}

deny_reasons contains "purpose is not permitted for principal" if {
	count(principal) > 0
	not input.request_purpose in object.get(principal, "purposes", [])
}

deny_reasons contains "agent authorization expired or invalid" if not expiry_is_future

expiry_is_future if {
	expiry_ns := time.parse_rfc3339_ns(input.expires_at)
	expiry_ns > time.now_ns()
}

deny_reasons contains "missing requested tool" if not input.requested_tool

deny_reasons contains "tool outside effective delegated scopes" if {
	input.requested_tool
	not input.requested_tool in object.get(principal, "allowed_tools", [])
}

deny_reasons contains "tool outside effective delegated scopes" if {
	input.requested_tool
	not input.requested_tool in input.agent_scopes
}

deny_reasons contains "tool outside effective delegated scopes" if {
	input.delegation_depth > 0
	not input.requested_tool in input.parent_scopes
}

reason := "OPA allows: principal, purpose, scopes and expiry are valid" if allow

reason := concat("; ", sort([message | deny_reasons[message]])) if not allow

result := {"allow": allow, "reason": reason}
