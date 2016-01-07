openerp.web_d3_chart = function(instance) {

    chart_d3_instance = 0;

    function get_chart_d3_instance() {
        chart_d3_instance += 1;
        return chart_d3_instance;
    };

    chart2resize = {};
    old_resize = window.onresize;

    window.onresize = function (e) {
        if (typeof old_resize == 'function') old_resize(e);
        _(_.keys(chart2resize)).each(function (instance) {
            chart2resize[instance](e);
        });
    }

    var _lt = instance.web._lt;
    var _t = instance.web._t;

    instance.web.views.add('chart-d3', 'instance.web_d3_chart.ChartD3View');

    instance.web_d3_chart.ChartD3View = instance.web.View.extend({
        events: {
            'click .graph_mode_selection img' : 'mode_selection',
            'click .oe_chart_d3_field_axis ul li.y-axis ul li' : 'field_axis_selection',
            'click .oe_chart_d3_field_axis ul li.y2-axis ul li' : 'field_axis_selection',
            'click .oe_chart_d3_field_axis ul li.printing ul li' : 'print_selection',
        },
        print_selection: function(event) {
            var ext = null;
            var img = null;
            var self = this;
            var title = this.ViewManager.action.name;
            var dashboard_actions = window.$('.oe_dashboard .oe_action');
            _(dashboard_actions).each(function(action){
                var act = $(action);
                if (act.find('.oe_chart_d3.oe_view')[0] === self.el){
                    title = act.find('.oe_header_txt').html().trim();
                }
            });
            var svg = this.$('svg');
            var svg_clone = svg.clone();
            d3.select(svg_clone[0]).selectAll('.nv-controlsWrap').remove();
            var wrap = d3.select(svg_clone[0]).select('.nv-legendWrap');
            var main_g = d3.select(svg_clone[0]).select('g');
            main_g.append('text')
                .style('text-anchor', 'middle')
                .style('font-size', '15px')
                .attr('y', parseInt(wrap.attr("transform").split(',')[1].replace(')','')))
                .attr('x', svg.width() / 2 - parseInt(main_g.attr("transform").split(',')[0].replace('translate(','')))
                .text(title);
            var tx = parseInt(main_g.attr("transform").split(',')[0].replace('translate(',''));
            var ty = parseInt(main_g.attr("transform").split(',')[1].replace(')','')) + 15;;
            main_g.attr('transform', 'translate('+ tx +','+ ty +')');
            if ($(event.currentTarget).hasClass('svg')) {
                ext = 'svg';
                img = (new XMLSerializer).serializeToString(svg_clone[0]);
            } else {
                var svg_string = "";
                try {
                    svg_string = svg_clone.html();
                } catch(e) {
                    /* 
                    Some browsers doesn't supported svg.html().
                    tested: svgObject.html() works on chrome 32 version and above
                    it doesn't works on chrome 29 version and previous
                    
                    #TODO:
                    Also, when using '(new XMLSerializer).serializeToString(svg[0]);'
                    I notice that when svg tag is present horizontal lines are hide. Probably a css 
                    case ?! can't really figure out why!
                    */
                    svg_string =  (new XMLSerializer).serializeToString(svg_clone[0]);
                }
                var canvas = this.$('canvas')[0];
                var DPI = 400;
                /* 1 inch = 96 px*/
                var scale = DPI / 96; 
                canvas.width = svg.width() * scale;
                canvas.height = svg.height() * scale;

                var ctx = canvas.getContext('2d');
                //ctx.font="10px Arial";
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.scale(scale, scale);
                if ($(event.currentTarget).hasClass('png')) {
                    ext = 'png';
                    canvg('canvas_' + this.element_id, svg_string, {
                        scaleWidth: scale.width,
                        scaleHeight: scale.height,
                        });
                    img = canvas.toDataURL();
                }
                if ($(event.currentTarget).hasClass('jpeg')) {
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    /* must be reput on black for filltext */
                    ctx.fillStyle = 'black';
                    ext = 'jpeg';
                    canvg('canvas_' + this.element_id, svg_string, {
                        ignoreClear: true,
                        scaleWidth: scale.width,
                        scaleHeight: scale.height,
                        });
                    img = canvas.toDataURL('image/jpeg');
                }
            }
            $.blockUI();
            self.session.get_file({
                url: '/web/chartd3/export',
                data: {
                    data: JSON.stringify({
                        ext: ext,
                        img: img,
                        title: title,
                    })},
                complete: $.unblockUI
            });
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
        set_autocomplete: function() {
            var self = this;
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

                    //$.ajax({
                    //    url: "/web/chartd3/autocomplete_data",
                    //    type: "POST",
                    //    contentType: "application/json",
                    //    data: JSON.stringify({"jsonrpc": "2.0",
                    //        "method": "call", "params": {model:self.dataset.model,searchText: request.term}, "id": 1
                    //    }),
                    //    dataType: "json",
                    //    success: function( data ) {
                    //        response( $.map( data.myData, function( item ) {
                    //            return {
                    //                label: item.id,
                    //                value: item.name
                    //            }
                    //        }));
                    //    }
                    //});


            $( "#showgraph" ).click(function() {
                self.reload();
            });
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
            $( "#start_date" ).datepicker({dateFormat: "yy-mm-dd",appendText: "(yyyy-mm-dd)"});
            $( "#end_date" ).datepicker({dateFormat: "yy-mm-dd",appendText: "(yyyy-mm-dd)"});

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
            
            if (this.d3_options.mode === 'pie'){
                this.$('.oe_chart_d3_field_axis .pie')[0].classList.remove("invisible");
                this.$('.oe_chart_d3_field_axis .multiBarAndStack')[0].classList.add("invisible");
            }else{
                this.$('.oe_chart_d3_field_axis .multiBarAndStack')[0].classList.remove("invisible");
                this.$('.oe_chart_d3_field_axis .pie')[0].classList.add("invisible");
            }
            nv.addGraph({

                generate: function() {
                    var width = 600,
                        height = 300;

                    var chart = nv.models.lineChart()
                        .width(width)
                        .height(height)
                        .margin({top: 20, right: 20, bottom: 20, left: 20});
                    chart.useInteractiveGuideline(true);
                    chart.dispatch.on('renderEnd', function(){
                        console.log('render complete');
                    });
                    //var chart = self.get_chart_mode(self.d3_options.mode);
                    var options = $.extend({}, self.d3_options);
                    self.apply_field_axis_options(chart, options);
                    //self.apply_d3_options(chart, options);
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
                    //d3.select(svg).datum(self.d3_data).transition().duration(500).call(chart);
                    //nv.utils.windowResize(function(){chart.update()});
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
            /*
                Modify also the context of the model to use this context in
                feature "Add in dashboard"
            */
            this.dataset._model._context.d3_options = this.d3_options;
        },
        get_chart_mode: function(charttype) {
            var self = this;
            var chart = null;
            if (charttype == "multiBarAndStack") {
                chart = nv.models.multiBar();
                chart.dispatch.on('stateChange', function(newState) {
                    var options = {controls: {}};
                    if (newState.stacked != undefined) {
                        options['controls']['stacked'] = newState.stacked;
                    }
                    if (newState.expanded != undefined) {
                        options['controls']['expanded'] = newState.expanded;
                    }
                    if (newState.showValues != undefined) {
                        options['controls']['show-values'] = newState.showValues;
                    }
                    if (newState.hideNullValues != undefined) {
                        options['controls']['hide-null-values'] = newState.hideNullValues;
                    }
                    if (newState.disabled != undefined) {
                        options['controls']['disabled_legend'] = newState.disabled;
                    }
                    self.d3_options = $.extend(true, {}, self.d3_options, options);
                    self.update_context();
                });
                this.$('.y2-axis').removeClass('invisible_case_2');
            }
            if (charttype == "line") {
                chart = nv.models.lineChart();
            }
            if (charttype == "pie") {
                chart = nv.models.pieChart();
                chart.dispatch.on('stateChange', function(newState) {
                    var options = {};
                    if (newState.labelType != undefined) {
                        options['label-type'] = {value: newState.labelType};
                    }
                    self.d3_options = $.extend(true, {}, self.d3_options, options);
                    self.update_context();
                });
                this.$('.y2-axis').addClass('invisible_case_2');
            }
            return chart;
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
        apply_d3_options: function(chart, options){
            var self = this,
                mode = this.d3_options.mode;
            _(_.keys(options)).each(function (option) {
                var o = options[option];
                if (option == 'y-axis') self.apply_d3_options_axis(chart, o, 'yAxis', 'field_axis_y');
                if (mode == 'multiBarAndStack' || mode == 'line') {
                    if (option == 'x-axis') self.apply_d3_options_axis(chart, o);
                    if (option == 'y2-axis') self.apply_d3_options_axis(chart, o, 'y2Axis', 'field_axis_y2');

                    if (option == 'reduce-x-ticks') chart.reduceXTicks(self.bool(o));
                    if (option == 'stagger-labels') chart.staggerLabels(self.bool(o));
                }if (mode == 'multiBarAndStack'){
                    if (option == 'rotate-labels') chart.rotateLabels(o.value); // angle
                }
                if (mode == 'pie') {
                    if (option == 'label-type') chart.labelType(o.value);
                    if (option == 'label-out-side') {
                        chart.pieLabelsOutside(o.value);
                        chart.donutLabelsOutside(o.value);
                    }
                    if (option == 'donut') chart.donut(self.bool(o));
                    if (option == 'tick-format') chart.valueFormat(d3.format(o.value));
                }

                if (option == 'controls') self.apply_d3_options_controls(chart, o);

                if (option == 'tool-tips') chart.tooltip(self.bool(o));
                if (option == 'margin') chart.margin(o);
                if (option == 'width') chart.width(o.value);
                if (option == 'height') chart.height(o.value);
                if (option == 'no-data') chart.noData(o.value); // str
            });
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
            var val = option.value || option;
            if (val == "1" || val == "true" || val == "True" || val == "TRUE") return true;
            return false;
        },
        apply_d3_options_controls: function(chart, options) {
            var self = this,
                mode = this.d3_options.mode;
            _(_.keys(options)).each(function (option) {
                var o = options[option];
                if (mode =='multiBarAndStack' || mode == 'line') {
                    if (option == 'stacked') chart.stacked(self.bool(o));
                    if (option == 'expanded') {
                        if (self.bool(o)) chart.stacked(true);
                        chart.expanded(self.bool(o));
                    }
                    if (option == 'disabled_legend') chart.state({disabled: o});
                    if (option == 'hide-null-values') chart.hideNullValues(self.bool(o));
                }

                if (option == 'show-controls') chart.showControls(self.bool(o));
                if (option == 'show-legend') chart.showLegend(self.bool(o));
                if (option == 'show-values') chart.showValues(self.bool(o));
            });
        },
        apply_d3_options_axis: function(chart, options, axis, field_axis) {
            var self = this,
                mode = this.d3_options.mode;
            _(_.keys(options)).each(function (option) {
                var o = options[option];
                if (mode == 'multiBarAndStack' || mode == 'line') {
                    if (option == 'label') chart[axis].axisLabel(o);
                    if (option == 'tick-format') chart[axis].tickFormat(d3.format(o));
                    if (option == 'show-max-min') chart[axis].showMaxMin(self.bool(o));
                    if (option == 'stagger-labels') chart[axis].staggerLabels(self.bool(o));
                    if (option == 'high-light-zero') chart[axis].highlightZero(self.bool(o));
                }if (mode == 'multiBarAndStack'){
                    if (option == 'rotate-labels') chart[axis].rotateLabels(o); // angle
                }

                //if (option == 'field_axis') chart[field_axis](o);
            });
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
        field_axis_selection: function(event) {
            var field_axis_field = event.target.getAttribute('data-choice');
            var claxis = event.target.getAttribute('data-axe');
            var txt = event.target.textContent;
            this.choose_field_axis(claxis, txt);
            this.d3_options[claxis].field_axis = field_axis_field;
            this.update_context();
            if (this.data_is_loaded) this.render_chart();
        },
        mode_selection: function(event) {
            this.$('.graph_mode_selection img').removeClass('active');
            $(event.currentTarget).addClass('active');
            var mode = event.currentTarget.getAttribute('data-mode');
            this.d3_options.mode = mode;
            this.update_context();
            if (this.data_is_loaded) this.render_chart();
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
        productName:function(){
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
                product:self.productName(),
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
            console.log("Sandeep");
            console.log(this.xaxis);
            console.log(this.xaxisOpts);
            console.log(this.yaxis);
            console.log(this.y2axis);
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
            this.set_autocomplete();
        },
        do_search: function(domain, context, group_by) {
            this.data_is_loaded = false;
            this.domain = domain;
            this.context = context;
            this.group_by = group_by;
            this.reload();
        },
        do_show: function() {
            this.do_push_state({});
            return this._super();
        },
    });
};
