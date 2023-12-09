#!/usr/bin/python3
from cmath import log
from mmap import ACCESS_DEFAULT
from os import ST_NODEV
from numpy.lib.shape_base import split
from dash import Dash,dcc,dash_table,html,Input, Output, ctx, callback,State,no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate


import pandas as pd
import plotly.express as px
import json
import base64
import io
import struct
import threading
import time
from collections import deque
import random
import socket
# df = None
session_counter = 0
max_cache_sessions = 50 #this server_side cache aimed for 1-2 users , localserver , few tabs. on other cases data corruption can happen
df_cache_per_user = [None]*max_cache_sessions
checklist_value = {"scaling": 2.0, "offset": 0.0}
checklistMeta = {"value": checklist_value}
add_field_btn_index = 1

CONTENT_STYLE = {
    "margin-left": "2rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    'height': '90vh',
   
}
CONTENT_STYLE2 = {
    "margin-left": "0rem",
    "margin-right": "0rem",
    "padding": "0rem 0rem",
    'height': '90vh',
   
}
CONTENT_STYLE3 = {
    "margin-left": "1rem",
    "margin-right": "0rem",
    "padding": "0rem 0rem",
    'height': '90vh',
    'background-color':"#EEE",
}

# STYLE_GREEN = {
#     'background-color': 'green',
#     'color': 'white',
# }

# STYLE_RED = {
#     'background-color': 'red',
#     'color': 'white',
# }

def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])

def load_preset_file(preset, filename='presets.json'):
    meta = dict()
    preset_opts=[]
    preset_filelist=[]
    with open(filename) as json_file:
        preset_filelist = json.load(json_file)
    for idx, val in enumerate(preset_filelist):
        preset_opts.append({
            "label": val["label"],
            "value": idx
        })
        if preset == val["value"]:
            if "meta" not in val or len(val["meta"]) == 0:
                for field in val["fields"]:
                    meta[field["value"]] = {"scaling": 1.0, "offset": 0.0}
            else:
                for field in val["meta"].keys():
                    meta[field] = {"scaling": val["meta"][field]["scaling"], "offset": val["meta"][field]["offset"]}
            
        preset_filelist[idx]['value']=idx #preset index
    return preset_filelist, preset_opts, meta

def generate_preset_dropdown():
    return dcc.Dropdown(
        options=[{'label': 'empty preset', 'value': 0}],
        value='0',
        multi=False,
        id="dropdown_presets",
        style={"width": "400px", "float":"left"}
    )

def generate_addfield_dropdown():
    return dcc.Dropdown(
        options=[],
        value='0',
        multi=False,
        id="dropdown_addfield",
    )


def generate_checklist():
    return html.Div([
        dcc.Checklist(
            options=[],
            value=[],
            
            id="checklist-input",
            labelStyle={"display":"block"}

        ),
        ], style={"height": "30vh", "overflow": "scroll"})
    

def generate_down_left_side():#need to think about the name
    return html.Div([
        html.Br(),
    
       dcc.Dropdown(
            options=[],
            value='0',
            multi=False,
            id="dropdown_addfield2",
        ),
            html.Div(
            [
                html.P("Scaling", style = {"display" : "inline", "width" : "10px", "margin" : "10px"}),
                dbc.Input(id = "scaling", debounce=True, value="1.0", type="text", style = {"display" : "inline", "width" : "80px"}),
                html.P(),
                html.P("Offset", style = {"display" : "inline", "width" : "10px", "margin" : "14.8px"}),
                dbc.Input(id = "offset", debounce=True, value="0.0", type="text", style = {"display" : "inline", "width" : "80px"})],
    ),], style={"height": "30vh", "overflow": "scroll"})    

        
        
    


def generate_leftpane(dataframe=0, max_rows=100):
    return html.Div([
        'Field checklist:',
        generate_checklist(),
        generate_down_left_side(),
        html.Button('remove fields', id='btn_fields_remove', n_clicks=0, className="button"),
        html.Button('add field', id='btn_fields_add', n_clicks=0, className="button"),
        html.Button('edit vline', id='btn_vline_edit', n_clicks=0, className="button"),
        html.Button('legend', id='btn_legend', n_clicks=0, className="button"),
        html.Br(),html.Br(),
        html.Button('preset Save', id='btn_preset_save', n_clicks=0, className="button-primary"),
        ])

app = Dash(__name__) # load all asset dir files (*.js , *.css)
app.layout = html.Div([
    html.Button('sidebar', id='sidebar-toggle', n_clicks=0, style={"float":"left", "margin-right": "10px"}),
    dcc.ConfirmDialogProvider(children=html.Button('Remove',style={"float":"left"}),id='presets-remove-btn',
        message='Are you sure you want to delete preset?',),
    html.Button('Add', id='presets-add-btn', style={"float":"left"}),
    generate_preset_dropdown(),
    dcc.Upload(html.Button('Open file', id='upload-data-btn'),id='upload-data', style={'float':'right'}),
    html.Button('Stream', id='stream_btn',style={'float':'right'}),
    html.Div(dcc.Slider(min=100, max=1000, step=50,value=300,id='my_slider',marks=None,tooltip={"placement": "bottom", "always_visible": True}),className="qwe",style={'float':'right',"width":"350px","margin-top": "10px"}),
    dcc.Interval(id='interval_stream',interval=200,n_intervals=0,disabled=True),
    html.H4('no file selected',id='upload-data-filelabel', style={'textAlign':'center'}),
    html.Br(),

    dbc.Modal(
        [
            dbc.ModalHeader("Remove Fields"),
            dbc.ModalBody(
                html.Div([
                    dcc.Checklist(
                        options=[],
                        value=[],
                        id="modal1_checklist",
                        style={"height": "60vh", "overflow": "scroll"},
                        labelStyle={"display":"block"})])),
            dbc.ModalFooter(
                dbc.Button(
                    "Delete", id="modal1-delete-btn", className="ml-auto", n_clicks=0
                )
            ),
        ],
        id="modal1",
        is_open=False,
    ),
    dbc.Modal(
        [
            dbc.ModalHeader("add field(press 'esc' to quit)"),
            dbc.ModalBody(generate_addfield_dropdown(),style={"height": "270px"}),
            dbc.ModalFooter(),
        ],
        id="modal2",
        is_open=False,
    ),
    dbc.Modal(
        [
            dbc.ModalHeader("add Preset(enter=save escape=cancel)"),
            dbc.ModalBody(
                html.Div([dcc.Input(id="modal3_presetAddInput", type='text',placeholder="new preset",debounce=True)])),
            dbc.ModalFooter(),
        ],
        id="modal3",
        is_open=False,
    ),
     html.Div(id="hidden_div2", style={"display":"none"}),
    dbc.Modal(
        [
            dbc.ModalHeader("add VLines"),
            dbc.ModalBody([
               dcc.Checklist(
                options=[],
                value=[],
                id='vlines_checklist',
                style={"height":"300px","overflow": "scroll"},
                labelStyle={"display":"block"}
                ),
                dcc.Input(id="modal4_vlineAddInput", type='text',placeholder="new vline",debounce=True),
                dcc.Input(id="modal4_vlineDelInput", type='text',placeholder="del vline",debounce=True),
        ]),
            dbc.ModalFooter(),
        ],
        id="modal4",
        is_open=False,
    ),
    dcc.ConfirmDialog(
        id='confirm-diag1',
        message='Danger danger! Are you sure you want to continue?',
    ),
    

    html.Div([
        html.Div([generate_leftpane()
        ],id="side-panel", className="three columns"),
        html.Div([dcc.Graph(id='main-graph',figure={},style=CONTENT_STYLE),
        ], id="page-content", style={"backgroundColor":"white"}, className="six columns"),
    ]),
    html.Div([
        html.Div([dcc.Graph(id='main-graph3',figure={},style=CONTENT_STYLE2)], id="page-content3", style=CONTENT_STYLE2, className="five columns"),

        html.Div([
            html.Div([dcc.Checklist(
            options=[],
            value=[],id="checklist-input3",labelStyle={"display":"block"}),
            ], style={"height": "30vh", "overflow": "scroll"}),
            html.Button('add field', id='btn_fields_add3', n_clicks=0, className="button"),
            dcc.Dropdown(options=[{'label': 'empty preset', 'value': 0}],
            value='0',multi=False,id="dropdown_presets3"),
            html.Br(),html.Br(),

            html.Div([dcc.Checklist(
            options=[],
            value=[],id="checklist-input4",labelStyle={"display":"block"}),
            ], style={"height": "30vh", "overflow": "scroll"}),
            html.Button('add field', id='btn_fields_add4', n_clicks=0, className="button"),
            dcc.Dropdown(options=[{'label': 'empty preset', 'value': 0}],
            value='0',multi=False,id="dropdown_presets4"),
        ],id="side-panel3", className="two columns",style=CONTENT_STYLE3),

        html.Div([dcc.Graph(id='main-graph4',figure={},style=CONTENT_STYLE2)], id="page-content4", style=CONTENT_STYLE2, className="five columns"),        
    ]),
    html.Div([
        dcc.Interval(id='interval_table',interval=200,n_intervals=0,disabled=True),
        html.Button('update table', id='btn_table1', n_clicks=0, className="button",style={}),
        html.Button('reset fields', id='btn_table2', n_clicks=0, className="button"),
        html.Button('all fields', id='btn_table3', n_clicks=0, className="button",style={'margin-right':'50px'}),
        html.Div([dcc.Dropdown(id='table_presets',options=[],value=None,),],id='table_presets_wrapper',style={"width": "400px","display":"inline-block","vertical-align": "bottom"}),
        html.Button('save preset', id='btn_table4', n_clicks=0, className="button",style={'margin-right':'50px'}),
        dcc.Input(id="input_new_preset", type='text',placeholder="add new preset",debounce=True,style={"width": "400px","display":"inline-block","vertical-align": "bottom"}),
        dcc.Dropdown(id='table_dropdown',options=['timetag',],value=['timetag'],multi=True),
        dash_table.DataTable(id='table1',data=[{}], columns=None,style_cell={'textAlign': 'left',},fill_width=False),
    ],style={'margin-top':'184vh'}),
    html.Div(id="hidden_div", style={"display":"none"}),
    dcc.Store(id="userid_store"),
    dcc.Store(id='store_metadata', data= {"value": {"scaling": 1.0, "offset": 0.0}}),
])

@app.callback(
    Output('vlines_checklist', 'options'),
    Output('vlines_checklist', 'value'), 
    Input('modal4_vlineAddInput', 'value'),
    Input('modal4_vlineDelInput', 'value'),
    Input('main-graph', 'clickData'),
    State('vlines_checklist', 'options'),
    State('vlines_checklist', 'value'),
    )
def vlines_list(addval,delval,gclick_data,listopt,listval):
    print ('vlines_list')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'modal4_vlineAddInput':
        listopt.append({'label': addval, 'value': addval})
        listval.append(addval)
        return listopt,listval
    elif button_id == 'modal4_vlineDelInput':
        listopt.remove({'label': delval, 'value': delval})
        listval.remove(delval)
        return listopt,listval
    else:
        pointx=gclick_data['points'][0]['x']
        listopt.append({'label': pointx, 'value': pointx})
        listval.append(pointx)
        return listopt,listval
    raise PreventUpdate

@app.callback(
    Output('table_presets', 'options'), 
    Input('table_presets_wrapper','n_clicks') ,
    )
def update_table_presets_options(n_clicks):
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'table_presets_wrapper' :
        print('update_table_presets_options',flush=True)
        options=[]
        with open('table_presets.json') as json_file:
            options = json.load(json_file)
        return options
    raise PreventUpdate

@app.callback(
    # Output('btn_table4', 'style'), 
    Output('table_presets_wrapper', 'n_clicks'),
    Input('btn_table4','n_clicks'),
    State('table_dropdown','value'),
    State('table_presets','value'),
    State('table_presets_wrapper', 'n_clicks'),
    )
def save_preset(n_clicks,value,preset_value,wrapper_clicks):
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'btn_table4':
        with open('table_presets.json','r+') as json_file:
            data = json.load(json_file)
            for entry in data:
                if entry['value'] == preset_value:
                    value.append(str(random.randint(1, 99999999999)))
                    entry['value'] = ','.join(value) # make entry['value'] unique even if fields are not
            json_file.seek(0)
            json.dump(data, json_file, indent=4)
            json_file.truncate() #delete any remaining chars when reducing file size
            return wrapper_clicks+1
    raise PreventUpdate

@app.callback(
    Output('table_dropdown', 'options'), 
    Output('table_dropdown', 'value'),
    Input('btn_table2','n_clicks') ,
    Input('btn_table3','n_clicks') ,
    Input('table_presets','value'),
    )
def update_table_dropdown_options(btn_table2_n_clicks,btn_table3_n_clicks,table_presets_value):
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'btn_table2' and len(recent_live_messages_dict):
        options = [key for adeque in recent_live_messages_dict.values() for key in adeque[-1]]
        value = ['timetag']
        return options,value
    if button_id == 'btn_table3' and len(recent_live_messages_dict):
        options = [key for adeque in recent_live_messages_dict.values() for key in adeque[-1]]
        value = options
        return options,value
    if button_id == 'table_presets' and len(recent_live_messages_dict):
        options = [key for adeque in recent_live_messages_dict.values() for key in adeque[-1]]
        value = table_presets_value.split(',')
        return options,value

    raise PreventUpdate

@app.callback(
    Output('btn_table1', 'style'),
    Output('interval_table', 'disabled'), 
    Input('btn_table1','n_clicks') ,
    State('btn_table1', 'style'), 
    )
def update_btn_table1_style(clicks,style):
    interval_table_disabled = None
    if clicks%2:
        style['background-color'] = 'green'
        style['color'] = 'white'
        interval_table_disabled = False
    else:
        style['background-color'] = 'white'
        style['color'] = 'black'
        interval_table_disabled = True
    return style,interval_table_disabled

@app.callback(
    Output('table1', 'data'), 
    Output('table1', 'columns'),
    Input('interval_table','n_intervals') ,
    State('btn_table1', 'n_clicks'),
    State('table_dropdown','value')
    )
def update_table1(interval_table_n_intervals,btn_table1_n_clicks,table_dropdown_value):
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'interval_table':
        # determine the number of rows and cols of the table based on the total items
        num_columns = min(max(2, int(len(table_dropdown_value)**0.5)), 4)
        num_rows = int(len(table_dropdown_value)/num_columns)+1
        column=[]
        data=[]
        row={}
        name_counter = -1
        for i in range(num_columns):
            column.append({"name": '_____________name__________', "id": 'col_{}'.format(2*i)})
            column.append({"name": 'value', "id": 'col_{}'.format(2*i+1)})
        for irow in range(num_rows):
            row={}
            for icol in range(num_columns):
                # check if fields list has enough values to populate this cell location
                if icol*num_rows+irow < len(table_dropdown_value):
                    name = table_dropdown_value[icol*num_rows+irow]
                    nvalue = None
                    #search name in database and get its value
                    for adeque in recent_live_messages_dict:
                        if name in recent_live_messages_dict[adeque][-1]:
                            nvalue = recent_live_messages_dict[adeque][-1][name]
                            break;
                    # append to row
                    row['col_{}'.format(icol*2)] = name
                    row['col_{}'.format(icol*2+1)] = nvalue
            data.append(row)
        return data,column
    raise PreventUpdate

@app.callback(
    Output('modal4', 'is_open'), 
    Input('btn_vline_edit', 'n_clicks')
    )
def btn_vline_edit(n_clicks):
    print ('btn_vline_edit')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'btn_vline_edit':
        return True
    raise PreventUpdate

@callback(
    Output("input_new_preset", "value"),
    Input("input_new_preset", "n_submit"),
    State("input_new_preset", "value"),
)
def input_new_preset(n_submit,value):
    if not value:
        raise PreventUpdate
    with open('table_presets.json','r+') as json_file:
        data = json.load(json_file)
        data.append({"label": value,"value": "timetag,{}".format(str(hash(value)))})
        json_file.seek(0)
        json.dump(data, json_file, indent=4)
        json_file.truncate() #delete any remaining chars when reducing file size
    return ''

@app.callback(
    Output('modal2', 'is_open'), 
    Input('btn_fields_add', 'n_clicks'),
    Input('btn_fields_add3', 'n_clicks'),
    Input('btn_fields_add4', 'n_clicks')
    )
def btn_fields_add_press(n_clicks,btn_fields_add3_click,btn_fields_add4_click):
    print ('btn_fields_add_press')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    global add_field_btn_index
    if button_id == 'btn_fields_add':
        add_field_btn_index = 1
        return True
    elif button_id == 'btn_fields_add3':
        add_field_btn_index = 3
        return True
    elif button_id == 'btn_fields_add4':
        add_field_btn_index = 4
        return True
    raise PreventUpdate



@app.callback(
    Output('modal1_checklist', 'options'), 
    Input('checklist-input', 'options'))
def modal1_write_checklist(options):
    print ('modal1_write_checklist')
    return options

@app.callback(
    Output('modal1', 'is_open'), 
    Output('modal1_checklist', 'value'),
    Input('btn_fields_remove', 'n_clicks'),
    Input('modal1-delete-btn', 'n_clicks'))

def btn_fields_remove_press(n_clicks,modal1closeclicks):
    print ('btn_fields_remove_press')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'btn_fields_remove':
        return True,[]
    elif button_id == 'modal1-delete-btn':
        return False,[]
    else:
        raise PreventUpdate

@app.callback(
    Output('side-panel', 'className'), 
    Output('page-content', 'className'),
    Input('sidebar-toggle', 'n_clicks'),
    )
def toggle_sidebar(n_clicks):
    print ('toggle_sidebar')
    if n_clicks%2==0:
        return "three columns","nine columns"
    else:
        return "hidden columns","twelve columns"


@app.callback(
    Output('my_slider', 'value'),
    Input('my_slider', 'value'),
    )
def set_recent_live_messages_maxlen(value):
    global recent_live_messages_dict
    for title in recent_live_messages_dict:
        recent_live_messages_dict[title] = deque(list(recent_live_messages_dict[title]), maxlen=value)
    raise PreventUpdate

@app.callback(
    Output('interval_stream', 'disabled'),
    Output('stream_btn', 'style'),
    Input('stream_btn', 'n_clicks'),
    State('stream_btn', 'style'),
    )
def set_interval_stream(n_clicks,style):
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'stream_btn':
        disabled = False
        if n_clicks%2:
            style['background-color'] = 'green'
            style['color'] = 'white'
            disabled = False
        else:
            style['background-color'] = 'white'
            style['color'] = 'black'
            disabled = True
        return disabled,style

@app.callback(
    Output('main-graph', 'figure'),
    Output('main-graph3', 'figure'),
    Output('main-graph4', 'figure'),
    Input('checklist-input', 'value'),
    Input('vlines_checklist', 'value'),
    Input('btn_legend', 'n_clicks'),
    Input('store_metadata', 'data'),
    Input('interval_stream', 'n_intervals'),
    Input('checklist-input3', 'value'),
    Input('checklist-input4', 'value'),
    State('userid_store','data'),
    State('interval_stream', 'disabled'),
    )
def update_figure(values, vlines, legend_counter,  meta_data,n_intervals,checklist_input3_value,checklist_input4_value, jsonuserid,interval_stream_disabled):
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'interval_stream':
        fig={};fig3={};fig4={}
        data = []
        for title in recent_live_messages_dict:
            data.extend(list(recent_live_messages_dict[title]))
        df = pd.DataFrame(data)
        if values:
            values.append("timetag")
            fig = px.line(df, x='timetag', y=list(values), markers=True)
        if checklist_input3_value:
            checklist_input3_value.append("timetag")
            fig3 = px.line(df, x="timetag", y=list(checklist_input3_value), markers=True)
            fig3.layout.update(showlegend=False,margin=dict(l=0, r=0, t=0, b=0))
        if checklist_input4_value:
            checklist_input4_value.append("timetag")
            fig4 = px.line(df, x="timetag", y=list(checklist_input4_value), markers=True)
            fig4.layout.update(showlegend=False,margin=dict(l=0, r=0, t=0, b=0))
        return fig,fig3,fig4

    if values == [] or not interval_stream_disabled:
        print ('return empty fig')
        return {},{},{}
    print('update figure')
    userid=json.loads(jsonuserid)
    filtered_df = df_cache_per_user[userid].loc[:, values]
    temp = filtered_df#add copy
    checklist_value.clear()

    for v in values:
        if v in meta_data.keys():
            temp[v] *= meta_data[v].get('scaling')
            temp[v] += meta_data[v].get('offset')

    fig = px.line(temp, x=temp.index, y=list(temp), markers=True)
    is_legend = True if legend_counter%2==0 else False
    fig.layout.update(showlegend=is_legend)
    for v in vlines:
        fig.add_vline(v, line_width=3, line_dash="dash", line_color="green")
    return fig,{},{}

@app.callback(
    Output('hidden_div2', 'children'), 
    Input('btn_preset_save', 'n_clicks'),
    State('checklist-input', 'options'),
    State('checklist-input', 'value'),
    State('dropdown_presets', 'value'),
    State('store_metadata', 'data'),
)
def save_preset(btn_preset_save_clicks,checklist_options,checklist_values,dropdown_presets_value, meta_data):
    print ('save_preset',btn_preset_save_clicks)

    if btn_preset_save_clicks == 0:
        raise PreventUpdate
    if dropdown_presets_value==0:
        raise PreventUpdate #keep first preset always empty

    preset_dict,preset_opts,meta = load_preset_file(dropdown_presets_value)
    preset_dict[dropdown_presets_value]['fields']=checklist_options
    preset_dict[dropdown_presets_value]['values']=checklist_values
    preset_dict[dropdown_presets_value]['meta']=meta_data

    with open('presets.json', 'w') as f:
        json.dump(preset_dict, f)
    raise PreventUpdate



@app.callback(
    
    Output('store_metadata', 'data'),
    Input('scaling', 'value'),
    Input('offset', 'value'),
    Input('checklist-input', 'options'),
    Input('dropdown_presets', 'value'),
    State('dropdown_addfield2', 'value'),
    
    State('store_metadata', 'data'),

)
def update_checklist_meta(scaling, offset, options, dropdown_presets_value, value, meta_data):
    print("update_checklist_meta")
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger_id = ctx.triggered_id
    if trigger_id == 'checklist-input' or trigger_id == 'dropdown_presets':
        a,b, meta_data = load_preset_file(dropdown_presets_value)
    meta_data_list = list(meta_data.keys())
    for v in options: #add values to metadata with default scling and offset
        if v["value"] not in meta_data_list:
            meta_data[v["value"]] = {"scaling": 1.0, "offset": 0.0}

    for v in list(meta_data.keys()):#remove values from metadata
        temp = {'label': v, 'value': v}
        if temp not in options:
            meta_data.pop(v)
    if value in list(meta_data.keys()):#add values to metadata with input scling and offset
        if isfloat(offset) and isfloat(scaling):
            meta_data[value] = {"scaling": float(scaling), "offset": float(offset)}

    return meta_data

def isfloat(num):#taken from https://www.programiz.com/python-programming/examples/check-string-number
    try:
        float(num)
        return True
    except ValueError:
        return False
@app.callback(
    Output('scaling', 'value'),
    Output('offset', 'value'),

    Input('dropdown_addfield2', 'value'),
    State('store_metadata', 'data')

)
def update_scaling_and_offset(value, meta_data):
    if value in list(meta_data.keys()):
        return str(float(meta_data[value]["scaling"])), str(float(meta_data[value]["offset"]))
    else:
        return "1.0", "0.0"


##############
@app.callback(
    Output('dropdown_addfield2', 'options'),
    Input('checklist-input', 'options'),
    Input('dropdown_addfield2', 'value'),
    Input('scaling', 'value'),
    Input('offset', 'value')
)

def update_dropdown_addfield2(n_clicks, value, vScanling, vOffset):
    checklist_value.clear()
    checklist_value["scaling"] = vScanling
    checklist_value["offset"] = vOffset
    return n_clicks
   
@app.callback(
    Output('checklist-input', 'options'),
    Output('checklist-input', 'value'),
    Input('dropdown_addfield', 'value'),
    Input('dropdown_presets', 'value'),
    Input('modal1-delete-btn', 'n_clicks'),
    State('dropdown_addfield', 'options'),
    State('checklist-input', 'options'),
    State('checklist-input', 'value'),
    State('modal1_checklist', 'value'),
    State('dropdown_presets', 'value'),
    State('store_metadata', 'data'),
)
def update_checklist_input(value,preset_value,modal1btnclicks,options,outputs,values,modal1Value, dropdown_presets_value, meta):
    print ('update_checklist_input')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'dropdown_addfield' and add_field_btn_index == 1:
        out = outputs.copy()
        opt = [x for x in options if x["value"] == value]
        if opt and opt[0] and opt[0] not in out:
            out.append(opt[0])
        return out,values
    elif button_id == 'dropdown_presets':
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets_value)
        if (preset_dict[preset_value]['fields']):
            # print (preset_dict[preset_value]['fields'])
            return preset_dict[preset_value]['fields'],preset_dict[preset_value]['values']
        return preset_dict[0]['fields'],[]
    elif button_id == 'modal1-delete-btn':
        opt = [x for x in outputs if x["value"] not in modal1Value]
        vals = [x for x in values if x not in modal1Value]
        return opt,vals
    else:
        raise PreventUpdate

@app.callback(
    Output('dropdown_presets3', 'options'),
    Input('dropdown_presets', 'options'),
)
def update_dropdown_presets3(dropdown_presets_options):
    print ('update_dropdown_presets3')
    return dropdown_presets_options

@app.callback(
    Output('dropdown_presets4', 'options'),
    Input('dropdown_presets', 'options'),
)
def update_dropdown_presets4(dropdown_presets_options):
    print ('update_dropdown_presets4')
    return dropdown_presets_options

@app.callback(
    Output('checklist-input3', 'options'),
    Output('checklist-input3', 'value'),
    Input('dropdown_presets3', 'value'),
    Input('dropdown_addfield', 'value'),
    State('checklist-input3', 'options'),
    State('dropdown_addfield', 'options'),
)
def update_checklist_input3(dropdown_presets3_value,dropdown_addfield_value,checklist_input3_options,dropdown_addfield_options):
    print ('update_checklist_input3')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'dropdown_presets3':
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets3_value)
        if (preset_dict[dropdown_presets3_value]['fields']):
            # print (preset_dict[preset_value]['fields'])
            return preset_dict[dropdown_presets3_value]['fields'],preset_dict[dropdown_presets3_value]['values']
        return preset_dict[0]['fields'],[]
    elif button_id == 'dropdown_addfield' and add_field_btn_index == 3:
        out = checklist_input3_options.copy()
        opt = [x for x in dropdown_addfield_options if x["value"] == dropdown_addfield_value]
        if opt and opt[0] and opt[0] not in out:
            out.append(opt[0])
        return out,no_update
    raise PreventUpdate
        

@app.callback(
    Output('checklist-input4', 'options'),
    Output('checklist-input4', 'value'),
    Input('dropdown_presets4', 'value'),
    Input('dropdown_addfield', 'value'),
    State('checklist-input4', 'options'),
    State('dropdown_addfield', 'options'),
)
def update_checklist_input4(dropdown_presets4_value,dropdown_addfield_value,checklist_input4_options,dropdown_addfield_options):
    print ('update_checklist_input4')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'dropdown_presets4':
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets4_value)
        if (preset_dict[dropdown_presets4_value]['fields']):
            # print (preset_dict[preset_value]['fields'])
            return preset_dict[dropdown_presets4_value]['fields'],preset_dict[dropdown_presets4_value]['values']
        return preset_dict[0]['fields'],[]
    elif button_id == 'dropdown_addfield' and add_field_btn_index == 4:
        out = checklist_input4_options.copy()
        opt = [x for x in dropdown_addfield_options if x["value"] == dropdown_addfield_value]
        if opt and opt[0] and opt[0] not in out:
            out.append(opt[0])
        return out,no_update
    raise PreventUpdate


@app.callback(
    Output('dropdown_presets', 'options'),
    Output('modal3', 'is_open'), 
    Output('modal3_presetAddInput', 'value'),
    
    Input('modal3_presetAddInput', 'n_submit'),
    Input('presets-remove-btn', 'submit_n_clicks'),
    Input('upload-data-btn', 'n_clicks'),
    Input('stream_btn', 'n_clicks'),
    Input('presets-add-btn', 'n_clicks'),
    State('modal3_presetAddInput', 'value'),
    State('dropdown_presets', 'options'),
    State('dropdown_presets', 'value'),
    State('store_metadata', 'data'),
)
def dropdown_presets_update(n_submit, n_clicks,load_btn_clicks,stream_btn_n_clicks,modal3clicks, value, options, dropdown_presets_value, meta):
    print ('dropdown_presets_update')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if button_id == 'modal3_presetAddInput':
        if value == None or value=="":
            raise PreventUpdate      
        print ('modal3_presetAddInput: adding value=',value)
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets_value)
        preset_dict.append({'label':value, 'value':len(preset_dict), 'fields':[], 'values':[]})
        preset_opts.append({'label': value, 'value': len(preset_opts)})
        with open('presets.json', 'w') as f:
            json.dump(preset_dict, f)
        return preset_opts,False,''
    elif button_id == 'presets-remove-btn':
        print ('presets-remove-btn: remove value=',dropdown_presets_value)
        if dropdown_presets_value == 0:
            raise PreventUpdate
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets_value)
        del preset_dict[dropdown_presets_value]
        del preset_opts[dropdown_presets_value]
        for idx,val in enumerate(preset_dict):
            if idx>=dropdown_presets_value:
                preset_dict[idx]["value"]=preset_dict[idx]["value"]-1
                preset_opts[idx]["value"]=preset_opts[idx]["value"]-1
        with open('presets.json', 'w') as f:
            json.dump(preset_dict, f)
        return preset_opts,no_update,no_update
    elif button_id == 'upload-data-btn':
        print ('upload-data-btn')
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets_value)
        return preset_opts,no_update,no_update
    elif button_id == 'stream_btn' and stream_btn_n_clicks==1:
        print ('stream_btn_n_clicks=',stream_btn_n_clicks)
        preset_dict,preset_opts,meta = load_preset_file(dropdown_presets_value)
        return preset_opts,no_update,no_update    
    elif button_id == 'presets-add-btn':
        return no_update,True,''
    raise PreventUpdate

# opens binary of floats with ascii csv header in the head.eg: field1,field2,field3,0floatArrayOf100Rows[3*100]
def binary2panda(bytes_io: io.BytesIO):
    content = bytes_io.read()
    header, data = content.split(b"\x00",maxsplit=1)
    
    # Split header into field names
    fields = header.decode().split(",")
    fields.pop() # remove last element from the list which is ",NULL"

    #slice data to complete rows
    row_bytes_len = len(fields)*4
    print ("slicing binary file to complete rows ",len(data)%row_bytes_len," bytes")
    data = data[:-(len(data)%row_bytes_len)]

    # Calculate number of rows and reshape data into a 2D array
    num_rows = len(data) // (len(fields) * 4)
    print ("number of rows: ",num_rows)
    data = struct.unpack("f"*num_rows*len(fields), data)
    data = [data[i:i+len(fields)] for i in range(0, len(data), len(fields))]

    # Convert data into a Pandas DataFrame
    return pd.DataFrame(data, columns=fields)

@app.callback(Output('upload-data-filelabel', 'children'),
              Output('dropdown_addfield','options'),
              Output('userid_store','data'),
              Input('upload-data', 'contents'),
              Input('btn_fields_add', 'n_clicks'),
              Input('btn_fields_add3', 'n_clicks'),
              Input('btn_fields_add4', 'n_clicks'),
              State('interval_stream', 'disabled'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def open_file_function(contents,n_clicks,n_clicks3,n_clicks4,interval_stream_disabled, filename, date):
    print ('open_file_function')
    # ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered_id
    if (button_id == 'btn_fields_add' or button_id == 'btn_fields_add3' or button_id == 'btn_fields_add4') and not interval_stream_disabled:
        msg = {}
        for title in recent_live_messages_dict:
            msg.update(recent_live_messages_dict[title][-1])
        opts = [{"label": field,"value": field} for field in msg]
        return "live",opts,json.dumps(0)

    if not contents:
        raise PreventUpdate 
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(
                    io.StringIO(decoded.decode('utf-8')),sep=",")
            elif 'xls' in filename:
                # Assume that the user uploaded an excel file
                df = pd.read_excel(io.BytesIO(decoded))
            elif '.bin' in filename:
                df = binary2panda(bytes_io=io.BytesIO(decoded))
        except Exception as e:
            print(e)
            return "error",[],{}

        dropdown_addfield_opts=[]
        for idx, val in enumerate(df.columns):
            dropdown_addfield_opts.append({
                "label": val,
                "value": val
            })
        # userid=str(uuid.uuid4())
        global session_counter
        session_counter += 1
        idx = session_counter%max_cache_sessions
        df_cache_per_user[idx] = df
        return filename,dropdown_addfield_opts,json.dumps(idx)
        # return filename,dropdown_addfield_opts,df.to_json(date_format='iso',orient='split')

def thread_loop(arg):
    UDP_IP = "234.0.0.1"
    UDP_PORT = 10005
    start_time = time.time()
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock1.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"UDP bind failed: {str(e)}",flush=True)
        return
    group = socket.inet_aton(UDP_IP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock1.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    global recent_live_messages_dict
    recent_live_messages_dict = {}
    while True:
        try:
            data, address = sock1.recvfrom(4096)
            d = json.loads(data.decode('utf-8'))
            # print (d[0]["fields"],flush=True)
            if d[0]['title'] not in recent_live_messages_dict:
                recent_live_messages_dict[d[0]['title']] = deque(maxlen=5*30)
            if "timetag" not in d[0]["fields"]:
                d[0]["fields"]["timetag"] = time.time() - start_time
            recent_live_messages_dict[d[0]['title']].append(d[0]["fields"])
        except Exception as e:
            print(f"while(true) fail: {str(e)}",flush=True)




if __name__ == '__main__':
    t1 = threading.Thread(target=thread_loop, args=(1,))
    # t1.daemon = True
    t1.start()
    app.run(host='127.0.0.1',port=8050, debug=False)
