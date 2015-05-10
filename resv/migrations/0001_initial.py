# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import resv.models
from django.conf import settings
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('date_of_birth', models.DateField()),
                ('first_name', models.CharField(max_length=40)),
                ('last_name', models.CharField(max_length=40)),
                ('email', models.EmailField(unique=True, max_length=255)),
                ('id_number', models.CharField(max_length=20)),
                ('is_guest', models.CharField(max_length=1)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('is_primary', models.BooleanField()),
                ('is_primary_family', models.BooleanField()),
                ('line1', models.CharField(max_length=40)),
                ('line2', models.CharField(max_length=40)),
                ('city', models.CharField(max_length=40)),
                ('state', models.CharField(max_length=2)),
                ('zip_code', models.CharField(max_length=5)),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
                ('person', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Blind',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=15)),
                ('capacity_parties', models.PositiveSmallIntegerField(blank=True)),
                ('capacity_hunters', models.PositiveSmallIntegerField(blank=True)),
                ('capacity_persons', models.PositiveSmallIntegerField(blank=True)),
                ('capacity_perparty', models.PositiveSmallIntegerField(blank=True)),
                ('shoot_days', models.CharField(max_length=7)),
                ('open_for_resvs', models.DateTimeField(default=resv.models.get_default_datetime)),
            ],
        ),
        migrations.CreateModel(
            name='Cluster',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='ClusterRanch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cluster', models.ForeignKey(to='resv.Cluster')),
            ],
        ),
        migrations.CreateModel(
            name='Family',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('joined', models.DateField()),
                ('number', models.CharField(max_length=10)),
                ('is_retired', models.BooleanField()),
                ('resv_freeze', models.BooleanField()),
                ('is_plus', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='GameRegion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('game', models.ForeignKey(to='resv.Game')),
            ],
        ),
        migrations.CreateModel(
            name='GameRegionRanch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('game_region', models.ForeignKey(to='resv.GameRegion')),
            ],
        ),
        migrations.CreateModel(
            name='GameType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='MastChangeLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('change_time', models.DateTimeField(auto_now_add=True)),
                ('change_type', models.CharField(max_length=40)),
                ('model_name', models.CharField(max_length=40)),
                ('instance_pk', models.PositiveIntegerField(blank=True)),
                ('initial_value', models.CharField(max_length=40)),
                ('new_value', models.CharField(max_length=40)),
                ('actor', models.ForeignKey(related_name='actor', to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(related_name='member', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='MembershipBlock',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='MembershipState',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=2)),
            ],
        ),
        migrations.CreateModel(
            name='MembershipStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='MembershipType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Ranch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=200)),
                ('size', models.PositiveIntegerField(blank=True)),
                ('city', models.CharField(max_length=200)),
                ('county', models.CharField(max_length=200)),
                ('comment', models.CharField(max_length=200)),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
                ('combo', models.CharField(max_length=24)),
                ('combo2', models.CharField(max_length=24)),
                ('allows_dogs', models.CharField(max_length=1)),
                ('archery_only', models.CharField(max_length=1)),
                ('open_for_resvs', models.DateTimeField(default=resv.models.get_default_datetime)),
            ],
        ),
        migrations.CreateModel(
            name='Resv',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('state', django_fsm.FSMField(default=b'Pending', max_length=50)),
                ('status', models.CharField(default=b'Pending', max_length=10, choices=[(b'Pending', b'Pending'), (b'Held', b'Held'), (b'Confirmed', b'Confirmed'), (b'Canceled', b'Canceled'), (b'Complete', b'Complete')])),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ResvSegment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('dog', models.PositiveIntegerField(default=0)),
                ('dog_comment', models.CharField(max_length=100, blank=True)),
                ('state', django_fsm.FSMField(default=b'Pending', max_length=50)),
                ('standby_state', models.PositiveIntegerField(default=0)),
                ('standby_updated', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(default=b'Pending', max_length=10, choices=[(b'Pending', b'Pending'), (b'Held', b'Held'), (b'Confirmed', b'Confirmed'), (b'Canceled', b'Canceled'), (b'Complete', b'Complete')])),
                ('blind', models.ForeignKey(to='resv.Blind')),
                ('game', models.ForeignKey(to='resv.Game')),
                ('resv', models.ForeignKey(to='resv.Resv')),
            ],
        ),
        migrations.CreateModel(
            name='ResvSegmentGuest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('guest_name', models.CharField(max_length=50)),
                ('is_hunting', models.BooleanField()),
                ('resv_segment', models.ForeignKey(to='resv.ResvSegment')),
            ],
        ),
        migrations.CreateModel(
            name='ResvSegmentPerson',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('is_hunting', models.BooleanField()),
                ('is_guest', models.BooleanField()),
                ('person', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('resv_segment', models.ForeignKey(to='resv.ResvSegment')),
            ],
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('desc', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='RuleRanch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ranch', models.ForeignKey(to='resv.Ranch')),
                ('rule', models.ForeignKey(to='resv.Rule')),
            ],
        ),
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('resv_open', models.DateField(default=datetime.date.today)),
                ('game_region', models.ForeignKey(to='resv.GameRegion')),
            ],
        ),
        migrations.CreateModel(
            name='SpecialDay',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('is_open', models.BooleanField(default=True)),
                ('ranch', models.ForeignKey(to='resv.Ranch')),
            ],
        ),
        migrations.AddField(
            model_name='gameregionranch',
            name='ranch',
            field=models.ForeignKey(to='resv.Ranch'),
        ),
        migrations.AddField(
            model_name='game',
            name='game_type',
            field=models.ForeignKey(to='resv.GameType'),
        ),
        migrations.AddField(
            model_name='family',
            name='block',
            field=models.ForeignKey(to='resv.MembershipBlock'),
        ),
        migrations.AddField(
            model_name='family',
            name='membership_state',
            field=models.ForeignKey(to='resv.MembershipState'),
        ),
        migrations.AddField(
            model_name='family',
            name='membership_type',
            field=models.ForeignKey(to='resv.MembershipType'),
        ),
        migrations.AddField(
            model_name='family',
            name='status',
            field=models.ForeignKey(to='resv.MembershipStatus'),
        ),
        migrations.AddField(
            model_name='clusterranch',
            name='ranch',
            field=models.ForeignKey(to='resv.Ranch'),
        ),
        migrations.AddField(
            model_name='blind',
            name='ranch',
            field=models.ForeignKey(to='resv.Ranch'),
        ),
        migrations.AddField(
            model_name='person',
            name='family',
            field=models.ForeignKey(to='resv.Family'),
        ),
        migrations.AddField(
            model_name='person',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='person',
            name='user_permissions',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions'),
        ),
    ]
