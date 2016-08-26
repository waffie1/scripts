<h1>Add User</h1>
<form action="/f5/admin/user_add" method="POST">
UserName <input type="text" size=16 name="username">
<input type="submit" Value="Add User">
</form>
<br>
<p>Enter a username that matches an Active Directory username.  The password
will be obtained from Active Directory.</p>
<br><br><br>


<h1>Edit Users</h1>
    {{!user_table}}

