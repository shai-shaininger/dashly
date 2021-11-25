#!/usr/bin/python3
from mmap import ACCESS_DEFAULT

from numpy.lib.shape_base import split
import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash.dash import no_update
import pandas as pd
import plotly.express as px
import json
import base64
import io
# import uuid

# df = None
session_counter = 0
max_cache_sessions = 50 #this server_side cache aimed for 1-2 users , localserver , few tabs. on other cases data corruption can happen
df_cache_per_user = [None]*max_cache_sessions

CONTENT_STYLE = {
    "margin-left": "2rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    'height': '90vh',
    # 'width': '100vw',
}

def generate_linegraph(dataframe=0, max_rows=100):
    return dcc.Graph(
        id='main-graph',
        figure={},
        style=CONTENT_STYLE
    )

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

def load_preset_file(filename='presets.json'):
    preset_opts=[]
    preset_filelist=[]
    with open(filename) as json_file:
        preset_filelist = json.load(json_file)
    for idx, val in enumerate(preset_filelist):
        preset_opts.append({
            "label": val["label"],
            "value": idx
        })
        preset_filelist[idx]['value']=idx #preset index
    return preset_filelist, preset_opts

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
        )
    ], style={"height": "60vh", "overflow": "scroll"})

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

def generate_leftpane(dataframe=0, max_rows=100):
    return html.Div([
        'Field checklist:',
        generate_checklist(),
        html.Button('remove fields', id='btn_fields_remove', n_clicks=0, className="button"),
        html.Button('add field', id='btn_fields_add', n_clicks=0, className="button"),
        html.Button('edit vline', id='btn_vline_edit', n_clicks=0, className="button"),
        html.Button('legend', id='btn_legend', n_clicks=0, className="button"),
        html.Br(),html.Br(),
        html.Button('preset Save', id='btn_preset_save', n_clicks=0, className="button-primary"),
        ])

app = dash.Dash(__name__) # load all asset dir files (*.js , *.css)
app.layout = html.Div([
    html.Button('sidebar', id='sidebar-toggle', n_clicks=0, style={"float":"left", "margin-right": "10px"}),
    dcc.ConfirmDialogProvider(children=html.Button('Remove',style={"float":"left"}),id='presets-remove-btn',
        message='Are you sure you want to delete preset?',),
    html.Button('Add', id='presets-add-btn', style={"float":"left"}),
    generate_preset_dropdown(),
    dcc.Upload(html.Button('Open file', id='upload-data-btn'),id='upload-data', style={'float':'right'}),
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
        html.Div([
            generate_leftpane()
        ],id="side-panel", className="three columns"),
        html.Div([
            generate_linegraph(),
        ], id="page-content", style={"backgroundColor":"white"}, className="nine columns"),
    ]),
    html.Div(id="hidden_div", style={"display":"none"}),
    dcc.Store(id="userid_store")
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
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
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
    Output('modal4', 'is_open'), 
    Input('btn_vline_edit', 'n_clicks')
    )
def btn_fields_remove_press(n_clicks):
    print ('btn_fields_remove_press')
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'btn_vline_edit':
        return True
    raise PreventUpdate

@app.callback(
    Output('modal2', 'is_open'), 
    Input('btn_fields_add', 'n_clicks')
    )
def btn_fields_remove_press(n_clicks):
    print ('btn_fields_remove_press')
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'btn_fields_add':
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
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
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
    Output('main-graph', 'figure'), 
    Input('checklist-input', 'value'),
    Input('vlines_checklist', 'value'),
    Input('btn_legend', 'n_clicks'),
    State('userid_store','data'),
    State('upload-data-filelabel','children')
    )
def update_figure(values,vlines,legend_counter,jsonuserid,filename):
    print ('update_figure')
    # global df
    if values == []:
        print ('return empty fig')
        return {}
    userid=json.loads(jsonuserid)
    filtered_df = df_cache_per_user[userid].loc[:, values]
    # dff = pd.read_json(jsonuserid,orient='split')
    # filtered_df = dff.loc[:, values]
    fig = px.line(filtered_df, x=filtered_df.index, y=list(filtered_df), markers=True)
    is_legend = True if legend_counter%2==0 else False
    fig.layout.update(showlegend=is_legend)
    for v in vlines:
        fig.add_vline(v, line_width=3, line_dash="dash", line_color="green")
    # df.arm[df.arm.diff() != 0].index[0]
    # print (df.arm[df.arm.diff() != 0].iloc[1])
    # fig.add_vline(x=df[df.arm > 0].index[0], line_width=3, line_dash="dash", line_color="green")
    return fig

@app.callback(
    Output('hidden_div', 'children'), 
    Input('btn_preset_save', 'n_clicks'),
    State('checklist-input', 'options'),
    State('checklist-input', 'value'),
    State('dropdown_presets', 'value'),
)
def save_preset(btn_preset_save_clicks,checklist_options,checklist_values,dropdown_presets_value):
    print ('save_preset',btn_preset_save_clicks)
    if btn_preset_save_clicks == 0:
        raise PreventUpdate
    if dropdown_presets_value==0:
        raise PreventUpdate #keep first preset always empty

    preset_dict,preset_opts = load_preset_file()
    preset_dict[dropdown_presets_value]['fields']=checklist_options
    preset_dict[dropdown_presets_value]['values']=checklist_values

    with open('presets.json', 'w') as f:
        json.dump(preset_dict, f)
    raise PreventUpdate

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
    )
def update_checklist_input(value,preset_value,modal1btnclicks,options,outputs,values,modal1Value):
    print ('update_checklist_input')
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'dropdown_addfield':
        out = outputs.copy()
        opt = [x for x in options if x["value"] == value]
        if opt and opt[0] and opt[0] not in out:
            out.append(opt[0])
        return out,values
    elif button_id == 'dropdown_presets':
        preset_dict,preset_opts = load_preset_file()
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
    Output('dropdown_presets', 'options'),
    Output('modal3', 'is_open'), 
    Output('modal3_presetAddInput', 'value'),
    Input('modal3_presetAddInput', 'n_submit'),
    Input('presets-remove-btn', 'submit_n_clicks'),
    Input('upload-data-btn', 'n_clicks'),
    Input('presets-add-btn', 'n_clicks'),
    State('modal3_presetAddInput', 'value'),
    State('dropdown_presets', 'options'),
    State('dropdown_presets', 'value'),
)
def dropdown_presets_update(n_submit, n_clicks,load_btn_clicks,modal3clicks, value, options, dropdown_presets_value):
    print ('dropdown_presets_update')
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'modal3_presetAddInput':
        if value == None or value=="":
            raise PreventUpdate      
        print ('modal3_presetAddInput: adding value=',value)
        preset_dict,preset_opts = load_preset_file()
        preset_dict.append({'label':value, 'value':len(preset_dict), 'fields':[], 'values':[]})
        preset_opts.append({'label': value, 'value': len(preset_opts)})
        with open('presets.json', 'w') as f:
            json.dump(preset_dict, f)
        return preset_opts,False,''
    elif button_id == 'presets-remove-btn':
        print ('presets-remove-btn: remove value=',dropdown_presets_value)
        if dropdown_presets_value == 0:
            raise PreventUpdate
        preset_dict,preset_opts = load_preset_file()
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
        preset_dict,preset_opts = load_preset_file()
        return preset_opts,no_update,no_update
    elif button_id == 'presets-add-btn':
        return no_update,True,''
    raise PreventUpdate

@app.callback(Output('upload-data-filelabel', 'children'),
              Output('dropdown_addfield','options'),
              Output('userid_store','data'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def open_file_function(contents, filename, date):
    print ('open_file_function')
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

if __name__ == '__main__':
    app.run_server(host='0.0.0.0',port=8050, debug=True)