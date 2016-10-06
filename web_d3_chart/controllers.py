# -*- coding: utf-8 -*-
import openerp.addons.web.http as openerpweb
from openerp.pooler import RegistryManager
import simplejson
import base64
import urllib2
from cStringIO import StringIO
import csv


class ChartD3(openerpweb.Controller):

    _cp_path = '/web/chartd3'

    @openerpweb.jsonrequest
    def autocomplete_data(self, request, model=None, searchText=None):
        obj = request.session.model(model)
        context = request.context
        registry = RegistryManager.get(request.session._db)
        if hasattr(registry.get(model), 'autocomplete_data'):
            return obj.autocomplete_data(
                model, searchText, context=context)

        view = request.session.model('ir.ui.view.chart.d3')
        return view.autocomplete_data(
            model, searchText, context=context)

    @openerpweb.jsonrequest
    def get_data(self, request, model=None, xaxis=None, yaxis=None, domain=None,
                 group_by=None, options=None,product=None,start_date=None,end_date=None):
        if domain is None:
            domain = []

        if group_by is None:
            group_by = []

        if options is None:
            options = {}

        obj = request.session.model(model)
        context = request.context
        registry = RegistryManager.get(request.session._db)
        if hasattr(registry.get(model), 'chart_d3_get_data'):
            return obj.chart_d3_get_data(
                xaxis, yaxis, domain, group_by, options,product,start_date,end_date,context=context)

        view = request.session.model('ir.ui.view.chart.d3')
        return view.get_data(
            model, xaxis, yaxis, domain, group_by, options, product,start_date,end_date,context=context)

    def content_disposition(self,request,filename):
        filename = filename.encode('utf8')
        escaped = urllib2.quote(filename)
        browser = request.httprequest.user_agent.browser
        version = int((request.httprequest.user_agent.version or '0').split('.')[0])
        if browser == 'msie' and version < 9:
            return "attachment; filename=%s" % escaped
        elif browser == 'safari':
            return "attachment; filename=%s" % filename
        else:
            return "attachment; filename*=UTF-8''%s" % escaped

    def from_data(self, fields, rows):
        fp = StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow([name.encode('utf-8') for name in fields])

        for data in rows:
            row = []
            for d in data:
                if isinstance(d, basestring):
                    d = d.replace('\n',' ').replace('\t',' ')
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False: d = None
                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @openerpweb.jsonrequest
    def get_locations(self, request, locationUsage=None):
        context = request.context
        obj = request.session.model('kpi_sheet.report')
        locations = []
        if hasattr(obj, 'getAllLocations'):
            locations = obj.getAllLocations(locationUsage, context=context)
        return locations

    @openerpweb.httprequest
    def export(self, request, data, token):
        kwargs = simplejson.loads(data)
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')

        location_name = kwargs.get('location_name').replace(" ", "_")
        location_id = kwargs.get('location_id')
        view_name = "kpi_data_store_{0}_{1}".format(location_id,location_name)

        model = kwargs.get('model')
        obj = request.session.model(model)
        registry = RegistryManager.get(request.session._db)
        if hasattr(registry.get(model), 'export_data'):
            data = obj.export_data(
                start_date,end_date,location_id, view_name)
            header = obj.export_header(
                start_date,end_date)
            return request.make_response(self.from_data(header, data),
                headers=[('Content-Disposition',
                            self.content_disposition(request,"ChartData.csv")),
                        ('Content-Type', 'text/csv;charset=utf8')],
                cookies={'fileToken': token})
        raise osv.except_osv(('Error'), ('Functionality not enabled'))
        # return request.make_response(self.from_data(header, data),
        #     headers=[('Content-Disposition',
        #                 self.content_disposition(self.filename(model))),
        #             ('Content-Type', self.content_type)],
        #     cookies={'fileToken': token})
