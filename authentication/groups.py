# korean_education_centre/authentication/groups.py

from django.contrib.auth.models import Group, Permission

def create_default_groups():
    # Admin Group
    admin_group, _ = Group.objects.get_or_create(name='Admins')
    admin_permissions = [
        'add_user', 'change_user', 'delete_user', 'view_user',
        'add_group', 'change_group', 'delete_group', 'view_group',
        'add_program', 'change_program', 'delete_program', 'view_program',
        'view_programapplication', 'change_programapplication',
        'add_student', 'change_student', 'delete_student', 'view_student',
        'add_activity', 'change_activity', 'delete_activity', 'view_activity',
    ]
    admin_group.permissions.set(Permission.objects.filter(codename__in=admin_permissions))

    # Lecturer Group
    lecturer_group, _ = Group.objects.get_or_create(name='Lecturers')
    lecturer_permissions = [
        'view_program',
        'view_programapplication', 'change_programapplication',
        'view_student',
        'add_activity', 'change_activity', 'view_activity',
    ]
    lecturer_group.permissions.set(Permission.objects.filter(codename__in=lecturer_permissions))

    # Student Group  
    student_group, _ = Group.objects.get_or_create(name='Students')
    student_permissions = [
        'view_program',
        'add_programapplication', 'view_programapplication',
        'view_activity',
    ]
    student_group.permissions.set(Permission.objects.filter(codename__in=student_permissions))