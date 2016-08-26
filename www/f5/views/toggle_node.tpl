<h1>Manage Node {{nodename}}</h1>
{{!pool_table}}

<br>
<br>
<h1>Node Status</h1>
{{!node_table}}
<br>
<h3>HELP</h3>
<b>ENABLE:</b> Enable the Node.  Traffic will begin using this node based on
<br>
load balancing rules, persistence, and any other slow start options.
<br>
<br>
<b>DISABLE:</b> Disable the Node.  No new sessions will be sent to this node.
<br>
Any persistent(sticky) sessions will remain on the node until the persistence
<br>
is no longer valid.
<br>
<br>
<b>FORCE DOWN</b> Disable the Node.  All traffic will immediately be moved
<br>
off this node based on the options defined in the pool for action on down.
<br>
This is the same action taken when the node fails its health check.
