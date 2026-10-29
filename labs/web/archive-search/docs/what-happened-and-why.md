# What Happened and Why

The search feature handles user input unsafely when it builds a database query. The database can interpret that input as part of the query itself, which may expose a record outside the public catalog.

Authentication alone does not prevent this data exposure. The search query and the records available to it both need appropriate controls.
