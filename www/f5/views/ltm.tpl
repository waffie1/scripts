<h1>Manage F5 Hardware</h1>

<h3>Add New</h3>
<h2>Add F5 Cluster</h2>
<form action="/f5/admin/hagroup_add" method="POST">
<table>
<tr>
<td>Name</td>
<td><input type="text" size=16 name="name"></td>
</tr><tr>
<td>Description</td>
<td><input type="text" size=16 name="description"></td>
</tr><tr>
<td></td>
<td><input type="submit" Value="Add Cluster"></td>
</tr>
</table>
</form>
<br><br>

<h2>Add F5 Hardware</h2>
<form action="/f5/admin/ltm_add" method="POST">
<table>
<tr>
<td>Hostname</td>
<td><input type="text" size=16 name="ltmname"></td>
</tr><tr>
<td>BigIP Version</td>
<td><select name="version">
<option value="BIG-IP_v11">V11</option></td>
</select>
</tr><tr>
<td>Cluster</td>
<td><select name="hagroup_id">
{{!select_options}}
</td>
</tr><tr>
<td></td>
<td><input type="submit" Value="Add LTM"></td>
</tr>
</table>
</form>
<h3>Manage Existing</h3>
{{!hagroup_tables}}

