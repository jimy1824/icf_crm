from django.contrib import admin
from .models import Employee, Role, Permission, EmployeeRole, RolePermission

admin.site.register(Employee)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(EmployeeRole)
admin.site.register(RolePermission)
