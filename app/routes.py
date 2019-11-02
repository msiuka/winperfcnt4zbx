from flask import render_template, redirect, url_for, request
from app import mssqlix
from app.forms import *
from werkzeug.utils import secure_filename
from extensions import *


@mssqlix.route('/')
def index():
    instances = Instances.select()
    if Counters.select().count() > 0:
        is_emptydb = False
    else:
        is_emptydb = True

    return render_template('index.html', **locals())


@mssqlix.route('/settings', methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    if perfcnt_winreg_import() is None:
        form.is_windows = False
    else:
        form.is_windows = True

    form.hide_filefields = is_perfcntfiles_exists()

    if form.validate_on_submit():
        if form.filter_regexp.data == "":
            form.filter_regexp.data = ".+"
        if form.current_host.data:
            counters_data, ids_data, descr_data = WindowsPerfCounterParser.get_perfcnt_from_win()
            fill_db(counters_data, ids_data, descr_data, form.filter_regexp.data)
        else:
            if form.hide_filefields:
                counters_data = readfile(cnt_filepaths[0], 'utf8')
                ids_data = readfile(cnt_filepaths[1], 'utf8')
                descr_data = readfile(cnt_filepaths[2], 'utf8')
            else:
                counters_data = readfile(secure_filename(form.counters_file.data.filename), 'utf8')
                ids_data = readfile(secure_filename(form.ids_file.data.filename), 'utf8')
                descr_data = readfile(secure_filename(form.descr_file.data.filename), 'utf8')

            fill_db(counters_data, ids_data, descr_data, form.filter_regexp.data)

        return redirect(url_for('index'))

    if request.method == 'GET':
        form.filter_regexp.data = 'MSSQL|SQLServer'

    return render_template('settings.html', form=form)


@mssqlix.route('/instance')
def instance():
    inst_id = request.args.get('id')

    selected_instance = Instances.get_by_id(inst_id)
    cnt_groups = CounterGroup.select().where(CounterGroup.instance_id == selected_instance)

    return render_template('instance.html', **locals())


@mssqlix.route('/group', methods=['GET', 'POST'])
def group():
    group_id = request.args.get('id')
    selected_group = CounterGroup.get_by_id(group_id)
    selected_instance = selected_group.instance_id
    cnt_group = Counters.select().where(Counters.counter_group_id == selected_group)
    group_params = Parameters.select().where(Parameters.counter_group_id == selected_group)

    parameters_list = []
    counters_list = []
    for param in group_params:
        parameters_list.append({'label': param.name, 'id': param.id, 'data': param.checked})
    for cnt in cnt_group:
        counters_list.append({'label': cnt.name, 'id': cnt.id, 'data': cnt.checked, 'description': cnt.description})

    form = boolean_form_builder(parameters_list, counters_list)

    if form.validate_on_submit():
        if form.all_param.data is True:
            for field in form:
                if 'parameter' in field.name:
                    field.data = True

        Parameters.save_form_data(form.data, 'parameter')
        Counters.save_form_data(form.data, 'counter')

        return redirect(url_for('instance', id=selected_instance.id))

    return render_template('group.html', **locals())


@mssqlix.route('/export', methods=['GET', 'POST'])
def export():
    form = ExportForm()
    form.messages.clear()
    selected_data = MSSQLixQueries.get_checked_counters_and_parameters()

    if len(selected_data) == 0:
        form.messages.append('No selected counters to export')

    if request.method == 'GET':
        form.zbx_url.data = "http://127.0.0.1/zabbix/"
        form.zbx_login.data = ""
        form.zbx_template_name.data = ""

    if form.validate_on_submit():
        try:
            new_template = form.zbx_api.template.create(
                host=form.zbx_template_name.data,
                groups={
                    "groupid": 1
                }
            )

            for instance in selected_data:
                if instance == EMPTY_INSTANCE_TEXT_REPRESENTATION:
                    export_instance = None
                else:
                    export_instance = instance
                for group in selected_data[instance]:
                    for cnt in selected_data[instance][group]['counters']:
                        if selected_data[instance][group]['parameters']:
                            for param in selected_data[instance][group]['parameters']:
                                exp_item = WindowsPerfCounterExporter(instance=export_instance,
                                                                      group_tuple=(
                                                                          group, selected_data[instance][group]['id']),
                                                                      counter_tuple=cnt,
                                                                      parameter=param)
                                result, msg = exp_item.zbx_item_create(zabbix_api=form.zbx_api,
                                                                       template=new_template,
                                                                       id_representation=bool(form.choise.data))
                                form.messages.append(msg)
                        else:
                            exp_item = WindowsPerfCounterExporter(instance=export_instance,
                                                                  group_tuple=(
                                                                      group, selected_data[instance][group]['id']),
                                                                  counter_tuple=cnt)
                            result, msg = exp_item.zbx_item_create(zabbix_api=form.zbx_api,
                                                                   template=new_template,
                                                                   id_representation=bool(form.choise.data))
                            form.messages.append(msg)

        except ZabbixAPIException as error:
            form.messages.append(error)

    return render_template('export.html', **locals())
