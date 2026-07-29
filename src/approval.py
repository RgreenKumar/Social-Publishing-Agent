VALID_STATUSES = [
    "Draft",
    "Pending Approval",
    "Approved",
    "Rejected",
    "Published",
    "Failed"
]

def approve_post():
    return "Approved"

def reject_post():
    return "Rejected"

def mark_pending():
    return "Pending Approval"

def mark_published():
    return "Published"

def mark_failed():
    return "Failed"