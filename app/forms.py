from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField
from wtforms.validators import InputRequired
from flask_wtf.file import FileField, FileRequired, FileAllowed
from pyzabbix import *


class SettingsForm(FlaskForm):
    counters_file = FileField('File with list of performance counters (*.txt)',
                              validators=[FileAllowed(['txt'])])
    ids_file = FileField('File with list of number representation of performance counters (*.txt)',
                         validators=[FileAllowed(['txt'])])
    descr_file = FileField('File with list of counters descriptions (*.txt)',
                           validators=[FileAllowed(['txt'])])
    current_host = BooleanField('Get data from current host')
    filter_regexp = StringField('RegExp filter string')
    is_windows = True
    hide_filefields = False
    submit = SubmitField('Get counters')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        result = True
        if self.current_host.data:
            return True
        else:
            if not self.hide_filefields:
                for field in [self.counters_file, self.ids_file]:
                    if field.data is None:
                        field.errors.append('Select *.txt file or get data from current host')
                        result = False
        return result


class BooleanListFormBase(FlaskForm):
    all_param = BooleanField(label='All parameters', default=False)
    submit = SubmitField('Save')

    descriptions = {}

    def validate(self):
        param_sum = 0
        cnt_sum = 0
        have_params = False
        if not FlaskForm.validate(self):
            return False
        result = True

        for field in self:
            if 'parameter' in field.name:
                have_params = True
            if 'parameter' in field.name and field.data is True:
                param_sum += 1
            if 'counter' in field.name and field.data is True:
                cnt_sum += 1

        if (self.all_param.data is True or param_sum > 0) and cnt_sum == 0:
            self.all_param.errors.append('Select counters')
            result = False
        if self.all_param.data is False and param_sum == 0 and cnt_sum > 0 and have_params:
            self.all_param.errors.append('Select parameters')
            result = False

        return result


def boolean_form_builder(parameters, counters):
    class BooleanListForm(BooleanListFormBase):
        pass

    for param in parameters:
        setattr(BooleanListForm, 'parameter_%d' % param['id'], BooleanField(label=param['label'], default=param['data']))

    for cnt in counters:
        setattr(BooleanListForm, 'counter_%d' % cnt['id'], BooleanField(label=cnt['label'], default=cnt['data']))
        BooleanListForm.descriptions['counter_%d' % cnt['id']] = cnt['description']

    return BooleanListForm()


class ExportForm(FlaskForm):
    zbx_url = StringField('Zabbix URL', validators=[InputRequired()])
    zbx_login = StringField('Zabbix login', validators=[InputRequired()])
    zbx_password = PasswordField('Zabbix password', validators=[InputRequired()])
    zbx_template_name = StringField('Zabbix template name', validators=[InputRequired()])
    choise = RadioField('Use numbers representation for performance counters',
                        choices=[(1, "Yes"), (0, "No, let's try use text representation")],
                        default=1,
                        coerce=int)
    submit = SubmitField('Create template!')
    zbx_api = None
    messages = []

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        result = True

        try:
            self.zbx_api = ZabbixAPI(self.zbx_url.data)
            self.zbx_api.login(self.zbx_login.data, self.zbx_password.data)
            finded_template = self.zbx_api.template.get(filter={"host": self.zbx_template_name.data})
            if finded_template:
                self.submit.errors.append("Template already exists")
                result = False
        except Exception as zbx_error:
            self.submit.errors.append(zbx_error)
            result = False

        return result
