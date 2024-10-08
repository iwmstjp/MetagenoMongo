from flask import Flask, request, render_template, send_file, current_app
import os
import pandas as pd
from werkzeug.utils import secure_filename
import io
import datetime
import subprocess
import hashlib
from werkzeug.datastructures import MultiDict
from collections import defaultdict
import logging

import module.load as load
import module.validation as data_validation
import module.email as email

app = Flask(__name__)

app.secret_key = os.urandom(10)
# Note: This application currently does not utilize cookies, session management, CSRF protection, or any features that require a consistent secret key.
# Therefore, we are using os.urandom() to generate a cryptographically secure random secret key at startup.
# This approach is suitable for the current use case, but if any features that depend on the secret key are introduced in the future,
# it will be necessary to ensure the secret key remains consistent across application restarts.
# Future developers should revisit this decision if the application's requirements change.
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
FIELDS_PER_ENTRY = 88 # the number of data columns. 

# --please comment out this part if you run the app on your labtop--
if os.getenv('META_REMOTE_PATH') is None or os.getenv('META_KEY_PATH') is None:
    current_app.logger.error("META_REMOTE_PATH or META_KEY_PATH is missing.")
    raise EnvironmentError("Required environment variables are not set.")
# --
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTIONS = load.load_options(os.path.join(SCRIPT_DIR, '.metagenomongo.csv'))
FIELDS = list(OPTIONS.keys())
FIELDS_WITH_NO = FIELDS[:]
FIELDS_WITH_NO.insert(0,'No')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS

def add_no_col(data):
    data['No'] = range(1, len(data.index) + 1)
    data = data.reindex(columns=FIELDS_WITH_NO, fill_value='')
    return data

def check_user(user_name):
    user_hashes = {'095c5883d62a373f59fe8934eacf70cab54e8c6b1f40889853410633fa70af10a6a008f46f974ca36ca6ab32d9a17408ea05b82075c30f7ee76c075989e64651',
    '11591a128deb1df58c2992102aee11b5b9f73632726b4100aa53ce25951b7441250ee1f704f18f128c822b281fe5865a0818c6c46db60cbfea0bc7004bb03f06',
    '1352bbc00c009babcde426f7bb97241ba263ef75c91d6dce416ef203b7699b84da5d0f775a0c57b525ba805435679aae7c7a2b80ce13508e639ae30e3e90e65b',
    '1be9d53d61a0813719d5041e3347725ef65e1eb74ad5526401978b0f1fc5872e31d1adbe9c6b12f68adb00dafbe71121e7722380375a55f8924cbdf175960bb9',
    '2c897d2e904e80f45384ea61b68bd8b9c502c5f746524c4db2647565be670f2aaa4e3b0ce7ea957450b0ffdcf284f7b0846f194e8496f9c269ad68199bff2ff7',
    '2d5ec49c491f0d69c25dffc1e6f309d0f5c637a04a24bc8f86f3ba4d6461a64ec33958dc469d0a11d9f742d48555cb2c3bbe1f3342d3f8ce6997c19fda2fab9e',
    '360313dc9b386d77cb9e5714dcce1b1f12cbe99c62d970c3b25292531e3d422bcc02a3721d94ab062ce8b8b198fcbf2a16c56952905e7632b5b1bb875e2d92d1',
    '3eb8c6e50085cdfc2f0f6e26588aacca987642e49cadde7eb07b9640a07c17d7cdd5349c178f7dc50ba32fb276b930258ffecac8422124b06f4b176579c6706d',
    '46d8796f09ec0d085cb0218b6aa0855d5b866e8ec6fa15db48d5c3b2465c3c5cabfef16324ea0db9dd52be3661d6446f412177f91d905272eeb538191219d4e8',
    '479fc2ff52801bcc1543c2c794ff9da522606b2b4f11cdcad34038d57808559b90f180b4e7ff8925f887930d2c46cdd8ca0da339e8d2cb8bc23930b8ab189391',
    '4f481093eef190f710b5f5b60be6353d02b53bbcae5158efa4e6d2f1c7fd50aa6388d974c28273f843adc94ceaf91eef46aba90859e58f1899e4c3e2266e43be',
    '58c6360c0fd9c03f13e16e2547ac85646022f017f332bc2e0c99a49aeafad96621b708a0ecef458e6918073b410474fe5b07a0db050e939464142b485e56f7db',
    '5b66037b3360fb6d539e6348ab9bb0913aa3d0144c32f1704998db7f48f299af67a06de95ccd287ea03e8dba773bc5d47f5b964ea4fcf374b7c6ac14cb9f1d26',
    '60d6e83e2789175394ab3181a3b77f35f2c6a42376615aae2ae5b58eee377ea6881e5a8d6bc31f1f77ef07f44868cb552b36eca0c5dc5ba7d8eb3c486a028dc4',
    '614ad84bdc3916df743efe7d56876c1dfd90d3556e2140accf66f566cdabb368f985a5ade002a74751daebb71577f7398a3b4d3604f2cc7a8fa14b6362f5eeb2',
    '77f9d952a4c5598f21ee9fd1984209f1d9082fc91dd0e2e7e66735f1148bfbdc4d0f3e959948bb21ec6dd3afd002a47a66a5783bda48fb015e9f94f87633d810',
    '837ddf09de71b3f9d5a23a2faac20bdee94921d7dd3d6e545b556d9493bee4b7e7efbe01d835cf47b03596725045eae0de74cdb12c811bc63bccfd012cf8b71a',
    '882ad57da0b93a930ca6b944b41cce5029691b1e076c702707f3e8691c28332d6779b5840dea1085861ce641d3cf5f6bf941034b4ca5c71b9d267ba10e8ca953',
    '8b2447e40564712c4da50c285b1f839bf65723e4c3abb3a49412ee20840f03bc4d02290b131531bf0ab64a092ed45700df46f60fb159d1d58df90bb5ac7458f9',
    '8ddd375de0c13e79f1c31bb16ed68c12a50c10dd55ee8c28fd71c81f785bc9d749334034c392a645b4be53d90b0c72e00a211e55da7abe62ccf3c5aa88f99ed3',
    '952a6c6959400519c7fda9264d0286c2c8c62f85f424140077483392806a572cc89597929a4307c26862bc6eec3fc0dd10677408706f8749225ea61aa7dd796a',
    '95e684dbba82f9d0a8120c2b985e68ad284349360c0c4a13ff246e1968c07fe1af4d2a4f8325508b7d7877f21555c013cff5ba73973d5afded414f78d27f6e5b',
    '97015c7461b4205b7402ba8dbde08c61ac7bdc6c4f813bcb651262ab4d52b4915c7cd045f19db653425e4b151c96a0158427ebc2f0bedfa95ab6a6150e7f60c5',
    'a866983a61957f1cd5c00ade200793f8e205290896c3c193b8ab2975d3d9d2b6c08e0d7d311363d8a1958d29c0f7d00896ee972204b33c2af41f351451319459',
    'b270d3b5835ef9ec5415889985d3533bb7622b5c1dcf329a7c629f2a32d9c51b851d305515a3656ed351569c641f721c55bf8cc29b83717886dac433c33908dd',
    'b2756793c3e7b559118af54c6862cb9e10d3353c078d10087bb894ab158b53e2afcd8d35f875062e30171e43837b9e672563d1d6e7876ed43c80e4ac019c7560',
    'b8b0abc97dba155f21f9a78d3a7161735f4c1d3947e0086f81b2d6f82fac4c051387932d0d6eba7f56f81fdd96398230ec3b74275a7cc24967bd016429c28ecb',
    'c24ce819f469b0f22c6ec9b94f7cc45a368c1c8e4b5de570f1a4c74e77291da951225ea7313b03d10ce155e68c583a2cb0f0e71fdc367b1b6d0316ef986f9935',
    'c9012f814eddbf3ae4d44a8673904518380be3f63080e940bdc6db97b9bab9d3dea58baf4a5eb3e48d04994de2e9086abb388cb00c6d3254b625ddd920607e68',
    'd4d06570e142345a42065af006215fa4eecc7bd4259816b02240e4ba1192f5c419aa8b1025cdae4149391b13804cb58eda4cfe4db8175d7304dfccba3735d2dd',
    'e4add73c741cd85e7a18c205ec9867362f96fefe0a1b6c6a2907e48e818be9a0f050d2a82a0d9ee36cdf1bb774070055c6ee777851005f6c05836deb88c0b9f7',
    'f0e9f1124f52fec5b6cd7c47a9cf9d5c5d6fb9df52c86a4dac2b05a50cc312968726d0360e5f3d3feee1de8a01cc6b4be954db4173d2a4cb9e556270d380cad7',
    'f3db14b942d882848294f5cdc38388840ac6ec5078acc510df38c275c6cf803196c99b79a5d1de187b0c9edf8512b63cad7c09872e648508af236ce5a1d8daf2',
    'fdfd1929b5aeb3c2cc759ad9aa8c8edec4318c38f12631f2ee2cb95a099ba07dbf59b43756b7e0de13d8d7e9040aefa0d6b41dad106c3ee4f7e199ea6e46b121'}
    user_hash = hashlib.sha3_512()
    user_hash.update(user_name.encode())
    return user_hash.hexdigest() in user_hashes

def parse_form_data(form_data):
    data_list = []
    tmp = []
    for key, value in form_data.items():
        if "_0" in key: # Skip No column
            tmp.extend(["", ""])# Add empty strings for 'delete' and 'duplicate'
            continue
        tmp.append(value)
        if str(FIELDS_PER_ENTRY) in key:
            data_list.append(tmp)
            tmp = []
    return data_list

def save_file_server(output_value,file_name,errors):
    remote_path = os.getenv('META_REMOTE_PATH')
    key_path = os.getenv('META_KEY_PATH')
    if remote_path is None or key_path is None:
        errors['warning'].append("Set META_KEY_PATH and/or META_REMOTE_PATH.")
        return
    # absolute path of the current directory
    path = os.getcwd()
    filepath = os.path.join(path, app.config['UPLOAD_FOLDER'], file_name)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(output_value)
        logging.info(f"File {file_name} saved successfully.")
    except FileNotFoundError:
        logging.error("File path does not exist.")
    except PermissionError:
        logging.error("Permission denied.")
    
    try:
        scp_command = ['scp', '-i', key_path, filepath, remote_path]
        subprocess.run(scp_command, check=True)
        email.send_email(file_name, remote_path) 
        logging.info(f"File successfully transferred to {remote_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred: {e}")
        logging.info("Run in the app root directory on the gpu2")
    finally:
        os.remove(filepath)

def empty_check(last_data):
    for n in last_data:     
        if n != "":
            return True
    return False

def custom_date_parser(x):
    if len(x) == 4:
        return pd.to_datetime(x, format='%Y').date()
    elif len(x) == 7:
        return pd.to_datetime(x, format='%Y-%m').date()
    else:
        return pd.to_datetime(x).date()

def handle_empty_data(data_list, data, errors, user_name):
    for l in data_list:
        for df in l:
            if df != "":
                return None
    errors["warning"].append("No Data")
    data = add_no_col(data)
    return render_template('index_with_table.html',
            tables=[data.to_html(classes='data', header="true")],
            errors=errors,
            df=data, user_name=user_name)

#remove user_name and action
#add Delete and Duplicate
def organize_form_data(values):
    values.popitem() # user_name
    values.popitem() # action
    values["Delete"] = ""
    values["Duplicate"] = ""

def clean_imported_file(data):
    # Strip whitespace from headers
    data.columns = data.columns.str.strip()
    # Strip whitespace from data
    data = data.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Replace NaN with empty strings
    data = data.fillna('')
    # Remove fully empty rows
    data = data[~(data == '').all(axis=1)]
    return data

def check_fields_of_imported_file(data, filepath, errors, values):
    # Get actual headers from the temporary DataFrame
    imported_fields = list(data.columns)
    # Identify headers in the input file that do not appear in the expected headers
    incorrect_fields = [header for header in imported_fields if header not in FIELDS]
    if incorrect_fields:
        os.remove(filepath)
        errors["fatal_error"].append("Input file contains unexpected fields :::" + ",".join(incorrect_fields))
        return render_template('index.html', \
            fields=FIELDS, values=values, errors=errors)

def read_imported_file(file, filepath, errors):
    file_name, ext = os.path.splitext(file.filename)
    if ext == '.csv':
        data = pd.read_csv(filepath, dtype=str, parse_dates=['collection_date', 'run_date'], date_format=custom_date_parser)  # Load as strings
    elif ext == '.xlsx':
        data = pd.read_excel(filepath, dtype=str, parse_dates=['collection_date', 'run_date'], date_format=custom_date_parser)
    else:
        os.remove(filepath)
        errors['fatal_error'].append('Invalid file type')
        return render_template('index_with_table.html', \
            tables=[data.to_html(classes='data', header="true")], errors=errors, df=data)
    return data

@app.route('/change', methods=['POST'])
def change():
    data_list = parse_form_data(request.form)
    errors = defaultdict(list)
    email.email_env_check(errors)
    data = pd.DataFrame(data_list, columns=FIELDS)
    data_validation.validation_all( FIELDS, OPTIONS, errors, data)
    data = add_no_col(data)
    return render_template('index_with_table.html', \
                tables=[data.to_html(classes='data', header="true")], \
                errors=errors, \
                df=data, user_name=request.form["user_name"])

@app.route('/addLine', methods=['POST'])
def addLine():
    data_list = parse_form_data(request.form)
    errors = defaultdict(list)
    email.email_env_check(errors)
    data = pd.DataFrame(data_list, columns=FIELDS)
    empty_response = handle_empty_data(data_list, data, errors, request.form["user_name"])
    if empty_response:
        return empty_response
    data_validation.validation_all( FIELDS, OPTIONS, errors, data)
    new_data = data.iloc[-1]
    if empty_check(new_data):
        data.loc[len(data)] = new_data
        data.at[len(data)-1,'sampleID'] = ''
    data = add_no_col(data)
    return render_template('index_with_table.html', \
                tables=[data.to_html(classes='data', header="true")], \
                errors=errors, \
                df=data, user_name=request.form["user_name"])

@app.route('/save', methods=['GET', 'POST'])
def save():
    data_list = parse_form_data(request.form)
    user_name = request.form["user_name"]
    errors = defaultdict(list)
    email.email_env_check(errors)
    data = pd.DataFrame(data_list, columns=FIELDS)
    data_validation.validation_all( FIELDS, OPTIONS, errors, data)
    data = data.drop(columns=['Delete', 'Duplicate'])
    data = data.loc[:, ~data.columns.str.contains('^Unnamed')]
    if errors['fatal_error']:
        data['Delete'] = ''
        data['Duplicate'] = ''
        data = add_no_col(data)
        return render_template('index_with_table.html', \
            tables=[data.to_html(classes='data', header="true")], errors=errors, \
            df=data, user_name=request.form["user_name"])
    output = io.StringIO()
    data.to_csv(output, index=False)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    current_time = datetime.datetime.now()
    file_name = user_name + current_time.strftime('_%Y-%m-%d-%H-%M-%S') +".csv"
    save_file_server(output.getvalue(),file_name,errors)
    return send_file(mem, mimetype='text/csv', \
                     as_attachment=True, download_name=file_name)

@app.route('/', methods=['GET', 'POST'])
def index():
    data = pd.DataFrame()
    errors = defaultdict(list)
    email.email_env_check(errors)
    values = {"default": 0}
    if request.method == 'POST':
        # Handle CSV upload
        user_name = request.form["user_name"]
        if not check_user(user_name):
            errors['fatal_error'].append('Unauthorized user. Please contact the database admin')
            return render_template('index.html', \
                tables=[data.to_html(classes='data', header="true")], fields=FIELDS, errors=errors, values=values, df=data)
        if 'file' in request.files:
            file = request.files['file']
            if file:
                path = os.getcwd()
                filename = secure_filename(file.filename)
                filepath = os.path.join(path, app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)
                except FileNotFoundError:
                    errors['fatal_error'].append('Please run it in the MetagenoMongo.')
                    return render_template('index_with_table.html', \
                        tables=[data.to_html(classes='data', header="true")], errors=errors, df=data)
                data = read_imported_file(file, filepath, errors)
                data = clean_imported_file(data)
                check_fields_of_imported_file(data, filepath, errors, values)
                data = data.reindex(columns=FIELDS, fill_value='')
                data_validation.validation_all(FIELDS, OPTIONS, errors, data) 
                data = add_no_col(data)
                os.remove(filepath)
                return render_template('index_with_table.html', \
                    tables=[data.to_html(classes='data', header="true")], \
                    errors=errors, df=data, user_name=user_name)
        # Handle manual data entry
        if request.form:
            values = MultiDict(request.form)
            if len(values) == 1: # importing file is not selected
                errors['fatal_error'].append('Choose an importing file.')
                return render_template('index.html', tables=[],\
                                        fields=FIELDS, errors=errors, values=values)
            organize_form_data(values)
            result = data_validation.data_assign(FIELDS, values)
            data = pd.DataFrame(result["data"],columns=FIELDS)
            user_name = request.form["user_name"]
            action = request.form["action"]
            if action == "new_line":
                new_data = data.iloc[-1]
                if empty_check(new_data):
                    data.loc[len(data)] = new_data
                    data.at[len(data)-1,'sampleID'] = ''
            data_validation.validation_all( FIELDS, OPTIONS, errors, data)
            data = add_no_col(data)
            return render_template('index_with_table.html', \
                    tables=[data.to_html(classes='data', header="true")], errors=errors, df=data, user_name=user_name)
    
    return render_template('index.html', tables=[], fields=FIELDS, errors=errors, values=values)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
