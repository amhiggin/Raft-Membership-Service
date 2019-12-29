# Raft Membership Service
A membership management system for a set of distributed nodes.

The system spec requires a number of services to be provided, including:
* Forming, joining, and leaving groups
* Monitoring group members and reporting member failures to the remaining members
* Returning the current group membership when required
* Possibly providing a ranking of members (e.g. based on age)

The spec requires that each member of the managed group should have a consistent view of group membership at any given time, i.e. at a minimum, they should see the same sequence of changes to group membership over time.


