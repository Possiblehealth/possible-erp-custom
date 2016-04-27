openerp.web_d3_chart = function(instance) {

    chart_d3_instance = 0;

    function get_chart_d3_instance() {
        chart_d3_instance += 1;
        return chart_d3_instance;
    };

    chart2resize = {};
    //old_resize = window.onresize;

   /* window.onresize = function (e) {
        if (typeof old_resize == 'function') old_resize(e);
        _(_.keys(chart2resize)).each(function (instance) {
            chart2resize[instance](e);
        });
    }*/

    var _lt = instance.web._lt;
    var _t = instance.web._t;

    instance.web.views.add('chart-d3', 'instance.web_d3_chart.ChartD3View');

    instance.web_d3_chart.ChartD3View = instance.web.View.extend({
        events: {

        },

        display_name: _lt('Chart'),
        view_type: 'chart-d3',
        template: 'Chart-d3',
        init: function(parent, dataset, view_id, options) {
            this._super(parent);
            this.action = parent;
            this.set_default_options(options);
            this.dataset = dataset;
            this.view_id = view_id;
            this.domain = [];
            this.context = {};
            this.group_by = [];
            this.element_id = 'chart-element-' + get_chart_d3_instance();
            this.d3_options = dataset.context.d3_options || {};
            this.init_d3_options();
            this.data_is_loaded = false;
            this.axis2read = [];
            this.session = parent.session;
        },
        apply_dynamic_changes: function() {
            var self = this;
            if (self.bool(self.d3_options["enable-autocomplete"])){
                $( "#autocomplete_field" ).autocomplete({
                    source: function( request, response ) {
                        self.rpc("/web/chartd3/autocomplete_data", {
                            model: self.dataset.model,
                            searchText: request.term
                        }).then(function (data) {
                            response($.map(data, function (item) {
                                return {
                                    label: item.name,
                                    value: item.id
                                }
                            }));
                        });
                    }});
                var option = self.d3_options["autocomplete-label"]
                if (typeof option === 'undefined' || option === null) {

                }else{
                    $( "#autocomplete-label").text(option.value);
                }
            }else{
                $( "#autocomplete-container").hide();
            }

            $( "#showgraph" ).click(function() {
                self.reload();
            });
            if (self.bool(self.d3_options["enable-download"])){
                $("#download_data").click(function() {
                    model = self.dataset.model;
                    self.session.get_file({
                        url: '/web/chartd3/export',
                        data: {
                            data: JSON.stringify({
                                start_date:self.startDate(),
                                model : model,
                                end_date:self.endDate()
                            })},
                        complete: $.unblockUI
                    });
                });
                var option = self.d3_options["download-label"];
                if (typeof option === 'undefined' || option === null) {

                }else{
                    $( "#download_data").html(option.value);
                }
            }else{
                $( "#download_data").hide();
            }

            $( "#start_date" ).datepicker({dateFormat: "yy-mm-dd"});
            $( "#end_date" ).datepicker({dateFormat: "yy-mm-dd"});

        },
        init_d3_options: function() {
            var options = {
                margin: {left: 90},
                height: {value: 400},
                menu: {all: 'true', 'y-axis': 'true', 'y2-axis': 'true'},
                'no-data': {value: _t('No data to display')},
                'x-axis': {field_axis: undefined},
                'y-axis': {field_axis: undefined},
                'y2-axis': {field_axis: undefined},
                controls: {},
            }
            this.d3_options = $.extend(true, {}, options, this.d3_options);
        },
        view_loading: function(r) {
            return this.load_chart(r);
        },
        render_chart: function() {
            var self = this;
            nv.addGraph({
                generate: function() {
                    var width = 600,
                        height = 300;
                    var zoom = 1;
                    var fitScreen = false;
                    var chart = nv.models.lineChart()
                        .width(width)
                        .height(height)
                        .margin({top: 30});
                    chart.useInteractiveGuideline(true);
                    chart.dispatch.on('renderEnd', function(){
                        console.log('render complete');
                    });
                    var options = $.extend({}, self.d3_options);
                    self.apply_field_axis_options(chart, options);
                    var svg = '#' + self.element_id + ' svg';

                    /*
                     Force to remove all the display before redraw
                     This sould be not necessary it's d3_chart responsability
                     we don't want actually take any risk about.
                     */
                    d3.select(svg).selectAll('g').remove();
                    d3.select(svg)
                        .attr('width', width)
                        .attr('height', height)
                        .datum(self.d3_data)
                        .call(chart);

                    setChartViewBox();
                    resizeChart();

                    nv.utils.windowResize(resizeChart);

                    d3.select('#zoomIn').on('click', zoomIn);
                    d3.select('#zoomOut').on('click', zoomOut);


                    function setChartViewBox() {
                        var w = width * zoom,
                            h = height * zoom;

                        chart
                            .width(w)
                            .height(h);

                        d3.select(svg)
                            .attr('viewBox', '0 0 ' + w + ' ' + h)
                            .transition().duration(500)
                            .call(chart);
                    }

                    function zoomOut() {
                        zoom += .25;
                        setChartViewBox();
                    }

                    function zoomIn() {
                        if (zoom <= .5) return;
                        zoom -= .25;
                        setChartViewBox();
                    }

                    // This resize simply sets the SVG's dimensions, without a need to recall the chart code
                    // Resizing because of the viewbox and perserveAspectRatio settings
                    // This scales the interior of the chart unlike the above
                    function resizeChart() {
                        var container = d3.select('#'+self.element_id);
                        var svg = container.select('svg');

                        if (fitScreen) {
                            // resize based on container's width AND HEIGHT
                            var windowSize = nv.utils.windowSize();
                            svg.attr("width", windowSize.width);
                            svg.attr("height", windowSize.height);
                        } else {
                            // resize based on container's width
                            var aspect = chart.width() / chart.height();
                            var targetWidth = parseInt(container.style('width'));
                            svg.attr("width", targetWidth);
                            svg.attr("height", Math.round(targetWidth / aspect));
                        }
                    }

                    return chart;
                },
                callback: function(graph) {
                    window.onresize = function() {
                        var width = nv.utils.windowSize().width - 40,
                            height = nv.utils.windowSize().height - 40,
                            margin = graph.margin();

                        if (width < margin.left + margin.right + 20)
                            width = margin.left + margin.right + 20;

                        if (height < margin.top + margin.bottom + 20)
                            height = margin.top + margin.bottom + 20;

                        graph.width(width).height(height);
                        var svg = '#' + self.element_id + ' svg';

                        d3.select(svg)
                            .attr('width', width)
                            .attr('height', height)
                            .call(graph);
                    };
                }

            });
        },
        destroy: function() {
            delete chart2resize[this.element_id];
            this._super();
        },
        update_context: function() {
            this.dataset.context.d3_options = this.d3_options;
            this.dataset._model._context.d3_options = this.d3_options;
        },

        parse_options: function(fields_view) {
            var self = this;
            var options = {menu: {}}
            if (!this.d3_options.mode) {
                options.mode = fields_view.arch.attrs.type;
            }
            _(this.get_nodes(fields_view, 'options', true)).each(function (option) {
                options[option.tag] = option.attrs;
            });
            options.menu[options.mode] = true;
            this.d3_options = $.extend(true, {}, this.d3_options, options);
        },
        apply_field_axis_options: function(chart, options) {
            var self = this;
            console.log("options");
            console.log(self.xaxisOpts);
            console.log(self.yaxis);
            var mode = this.d3_options.mode;
            var xLabel = this.xaxisOpts[this.xaxis].label;
            var xTickFormat = this.xaxisOpts[this.xaxis]["tick-format"];
            if(xTickFormat){
                if(xTickFormat == 'd'){
                    chart.xAxis.tickFormat(function(d) {
                        // Will Return the date, as "%m/%d/%Y"(08/06/13)
                        return d3.time.format('%x')(new Date(d))
                    });
                }else{
                    chart.xAxis.tickFormat(d3.format(xTickFormat));
                }
            }
            if(xLabel){
                chart.xAxis.axisLabel(xLabel);
            }

            var yoptions = this.yaxis[this.d3_options['y-axis'].field_axis];
            if (yoptions != undefined) {
                _(_(yoptions).keys()).each( function (option) {
                    var o = yoptions[option];
                    if (mode == 'multiBarAndStack') {
                        if (option == 'stacked' || option == 'expanded') 
                            if (self.group_by.length > 1)
                                if (options['controls'][option] == undefined) 
                                    options['controls'][option] = o;

                        if (option == 'label' || option == 'tick-format') 
                            options['y-axis'][option] = o
                    }

                    if (mode == 'pie') {
                        if (options[option] == undefined)
                            options[option] = {value: o};
                    }
                    if (mode == 'line') {
                        if (option == 'label')
                            chart.yAxis.axisLabel(o.value);
                        if (option == 'tick-format'){
                            if(o == 'd'){
                                chart.yAxis.tickFormat(function(d) {
                                    // Will Return the date, as "%m/%d/%Y"(08/06/13)
                                    return d3.time.format('%x')(new Date(d))
                                });
                            }else{
                                chart.yAxis.tickFormat(d3.format(o.value));
                            }

                        }
                    }
                });
            } else options['y-axis'] = {field_axis: undefined};
            var y2options = this.yaxis[this.d3_options['y2-axis'].field_axis];
            if (y2options != undefined) {
                _(_(y2options).keys()).each( function (option) {
                    var o = y2options[option];
                    if (mode == 'multiBarAndStack') {
                        if (option == 'label' || option == 'tick-format') 
                            options['y2-axis'][option] = o
                    }
                    if (mode == 'line') {
                        if (option == 'label')
                            chart.yAxis().axisLabel(o.value);
                        if (option == 'tick-format'){
                            if(o == 'd'){
                                chart.yAxis.tickFormat(function(d) {
                                    // Will Return the date, as "%m/%d/%Y"(08/06/13)
                                    return d3.time.format('%x')(new Date(d))
                                });
                            }else{
                                chart.yAxis().tickFormat(d3.format(o.value));
                            }

                        }
                    }
                });
            } else options['y2-axis'] = {field_axis: undefined};
        },
        bool: function(option){
            if (typeof option === 'undefined' || option === null) {
                return false;
            }
            var val = option.value || option;
            if (val == "1" || val == "true" || val == "True" || val == "TRUE") return true;
            return false;
        },
        add_field_axiss_to_options: function(claxis, yaxis, field_axis) {
            var self = this;
            var $select = this.$('nav.oe_chart_d3_field_axis ul li.' + claxis + ' ul');
            _($select.children()).each(function (node) {
                node.remove();
            });
            this.dataset.call('fields_get', [yaxis]).then(function (fields){
                
                $select.append(
                    _.map(_.union([], [undefined], yaxis), function (field) {
                        var str = _lt('Masqué');
                        if (field == undefined){
                            fields[undefined] = {string: str};
                        } else {
                            str = fields[field].string;
                        } 
                        return $('<li>').append($('<a>')
                                        .attr('data-choice', field)
                                        .attr('data-axe', claxis)
                                        .text(str));
                    })
                );
                var str = fields[field_axis].string;
                self.choose_field_axis(claxis, str);
            });
        },
        choose_field_axis: function(claxis, string) {
            var $label = this.$('nav.oe_chart_d3_field_axis ul li.' + claxis + ' a.label');
            $label.html(string + ' <span class="caret"></span>');
        },
        get_nodes: function(fields_view, tag, children) {
            var node = null;
            _(fields_view.arch.children).each(function (child) {
                if (child.tag == tag) {
                    if (children) node = child.children;
                    else node = child.attrs.field;
                }
            });
            return node;
        },
        get_fieldname: function(fields_view, axis) {
            var nodes = '';
            _(this.get_nodes(fields_view, axis, true)).each(function (field) {
                nodes = field.attrs.name;
            });
            return nodes;
        },
        get_yaxis: function(fields_view, axis) {
            var nodes = {};
            _(this.get_nodes(fields_view, axis, true)).each(function (field) {
                nodes[field.attrs.name] = field.attrs
            });
            console.log("called wiht axis="+axis);
            console.log(nodes);
            return nodes;
        },
        apply_yn_axis: function(node, values, field_axis){
            if (values.length) {
                if (this.bool(this.d3_options.menu[node])){
                    this.$('.' + node).removeClass('invisible');
                }
                if (!field_axis) {
                    if (node != 'y2-axis'){
                        field_axis = values[0];
                        this.d3_options[node].field_axis = values[0];
                    }else{
                        field_axis = undefined;
                        this.d3_options[node].field_axis = undefined;
                    }
                }
                this.add_field_axiss_to_options(node, values, field_axis);
                this.axis2read = _.union([], this.axis2read, values);
            }
        },
        autocomplete_data:function(){
            return $('#autocomplete_field').val();
        },
        startDate:function(){
            var date = $('#start_date').datepicker({ dateFormat: 'yyyy-mm-dd' }).val();
            return date;

        },
        endDate:function(){
            var date = $('#end_date').datepicker({ dateFormat: 'yyyy-mm-dd' }).val();
            return date;
        },

        reload: function(){
            var self = this,
                model = this.dataset.model,
                domain = this.domain || [],
                context = this.context || {},
                group_by = this.group_by || [];

            this.rpc("/web/chartd3/get_data", {
                model: model,
                xaxis: this.xaxis,
                yaxis: this.axis2read,
                domain: domain,
                group_by: group_by,
                options: this.d3_options,
                product:self.autocomplete_data(),
                start_date:self.startDate(),
                end_date:self.endDate(),
                context: context}).then(function(data_and_options) {
                    self.d3_data = data_and_options[0];
                    self.d3_options = data_and_options[1];
                    self.render_chart();
                    self.data_is_loaded = true;
                });
        },
        load_chart: function(fields_view) {
            var self = this;
            console.log("fields_view");
            console.log(fields_view);
            this.xaxisOpts = this.get_yaxis(fields_view, 'x-axis');
            this.xaxis = this.get_fieldname(fields_view, 'x-axis');
            this.yaxis = this.get_yaxis(fields_view, 'y-axis');
            var yaxis = _(this.yaxis).keys();
            this.y2axis = this.get_yaxis(fields_view, 'y2-axis');
            var y2axis = _(this.y2axis).keys();
            if (!y2axis.length){
                this.y2axis = this.yaxis;
                y2axis = yaxis;
            }

            this.parse_options(fields_view);
            this.apply_yn_axis('y-axis', yaxis, this.d3_options['y-axis'].field_axis);
            this.apply_yn_axis('y2-axis', y2axis, this.d3_options['y2-axis'].field_axis);
            _(_.keys(this.d3_options.menu)).each(function (chart) {
                if (self.bool(self.d3_options.menu[chart]) && self.bool(self.d3_options.menu.all)) {
                    var $chart = self.$('.' + chart);
                    $chart.removeClass('invisible');
                    if (chart == self.d3_options.mode) {
                        $chart.addClass('active');
                    }
                }
            });
            this.apply_dynamic_changes();
        }
    });
};
