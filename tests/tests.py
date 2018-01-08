from unittest import TestCase

from django.test import TestCase as DjangoTestCase
from django.test.utils import override_settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import reverse

from decimal import Decimal
import datetime

from django_tex.core import run_tex, compile_template_to_pdf, render_template_with_context
from django_tex.core import TexError

from django_tex.engine import engine

from django_tex.views import render_to_pdf

from tests.models import TemplateFile, Entry

class RunningTex(TestCase):

    def test_run_tex(self):
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        This is a test!\n\
        \\end{document}"

        pdf = run_tex(source)
        self.assertIsNotNone(pdf)

    def test_tex_error(self):
        source = "\
        \\documentclass{article}\n\
        \\begin{document}\n\
        This is a test!\n"

        with self.assertRaises(TexError):
            pdf = run_tex(source)

class ComplingTemplates(TestCase):

    def test_compile_template_to_pdf(self):
        template_name = 'tests/test.tex'
        context = {
            'test': 'a simple test', 
            'number': Decimal('1000.10'), 
            'date': datetime.date(2017, 10, 25),
            'names': ['Arjen', 'Jérôme', 'Robert', 'Mats'], 
        }
        pdf = compile_template_to_pdf(template_name, context)
        self.assertIsNotNone(pdf)

class RenderingTemplates(TestCase):

    def test_render_template(self):
        template_name = 'tests/test.tex'
        context = {
            'test': 'a simple test', 
            'number': Decimal('1000.10'), 
            'date': datetime.date(2017, 10, 25),
            'names': ['Arjen', 'Jérôme', 'Robert', 'Mats'], 
        }
        output = render_template_with_context(template_name, context)
        self.assertIn('\\section{a simple test}', output)
        self.assertIn('This is a number: 1000,10.', output)
        self.assertIn('And this is a date: 25.10.2017.', output)
        self.assertIn('\\item Arjen', output)

class Engine(DjangoTestCase):

    def render_template(self, template_string, context):
        template = engine.from_string(template_string)
        return template.render(context)

    def test_whitespace_control(self):
        context = {'foo': 'bar'}
        template_string="\\section{ {{- foo -}} }"
        output = self.render_template(template_string, context)
        self.assertEqual(output, '\\section{bar}')

    @override_settings(LANGUAGE_CODE='en')
    def test_override_l10n_setting(self):
        context = {'foo': Decimal('1000.10')}
        template_string="{{ foo|localize }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, '1000.10')

    @override_settings(LANGUAGE_CODE='de-de')
    def test_localize_decimal(self):
        context = {'foo': Decimal('1000.10')}
        template_string="{{ foo|localize }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, '1000,10')
    
    @override_settings(LANGUAGE_CODE='de-de')
    def test_localize_date(self):
        context = {'foo': datetime.date(2017, 10, 25)}
        template_string="{{ foo|localize }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, '25.10.2017')

    @override_settings(LANGUAGE_CODE='de-de')
    def test_format_long_date(self):
        context = {'foo': datetime.date(2017, 10, 25)}
        template_string="{{ '{:%d. %B %Y}'.format(foo) }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, '25. Oktober 2017')

    def test_rendering_unicode(self):
        context = {'foo': 'äüß'}
        template_string="{{ foo }}"
        output = self.render_template(template_string, context)
        self.assertEqual(output, 'äüß')

    def test_linebreaks(self):
        context = {
            'brecht': 
            'Ich sitze am Straßenhang.\n' +
            'Der Fahrer wechselt das Rad.'
        }
        template_string="{{ brecht | linebreaks }}"
        output = self.render_template(template_string, context)
        self.assertEqual(
            output, 
            'Ich sitze am Straßenhang.\\\\\n'+
            'Der Fahrer wechselt das Rad.'
        )

class Models(TestCase):
    '''
    TeXTemplateFile contains the relative path to a tex template (e.g. django_tex/test.tex)
    and validates if this template can be loaded.abs

    Since TeXTemplateFile is an abstract base class, it is used here in a subclassed version 'TemplateFile'
    '''

    def test_validation(self):
        TemplateFile(title='valid', name='tests/test.tex').full_clean()

        with self.assertRaises(ValidationError):
            TemplateFile(title='invalid', name='template/doesnt.exist').full_clean()

class Views(TestCase):

    def test_render_to_pdf(self):
        template_name = 'tests/test.tex'
        context = {
            'test': 'a simple test', 
            'number': Decimal('1000.10'), 
            'date': datetime.date(2017, 10, 25),
            'names': ['Arjen', 'Jérôme', 'Robert', 'Mats'], 
        }
        response = render_to_pdf(template_name, context, filename='test.pdf')
        self.assertIsInstance(response, HttpResponse)
        self.assertEquals(response['Content-Type'], 'application/pdf')
        self.assertEquals(response['Content-Disposition'], 'filename="test.pdf"')

class TestSite(DjangoTestCase):

    def test_entry_list_pdf(self):
        response = self.client.get(reverse('entry_list_pdf'))
        self.assertEqual(response.status_code, 200)

    def test_entry_list(self):
        response = self.client.get(reverse('entry_list'))
        self.assertEqual(response.status_code, 200)

    def test_entry_archive(self):
        Entry.objects.create(date=datetime.date(2017,1,1))
        response = self.client.get(reverse('entry_archive', args=(2017,)))
        self.assertEqual(response.status_code, 200)