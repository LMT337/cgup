import os, csv, glob, datetime, subprocess, getpass, socket
from shutil import copyfile

working_dir = '/gscmnt/gc2783/qc/CCDGWGS2018/dev'
os.chdir(working_dir)

date = datetime.datetime.now().strftime("%m-%d-%y")
hour_min = datetime.datetime.now().strftime("%H%M")
date_time = datetime.datetime.now().strftime("%m%d%y")

user = getpass.getuser()
host = socket.gethostname().split('.')[0]


def is_int(string):
    try:
        int(string)
    except ValueError:
        return False
    else:
        return True


woid_dirs_unfiltered = glob.glob('285*')
woid_dirs = []


for woid in filter(is_int, woid_dirs_unfiltered):
    woid_dirs.append(woid)

print(woid_dirs)


def workflow_create(woid):
    workflow_outfile = woid + '.workflow.'+ date_time + '.tsv'
    workflow = []
    while True:
        workflow_line = input()
        if workflow_line:
            workflow.append(workflow_line)
        else:
            break
    with open(workflow_outfile, 'w') as wfoutcsv:
        workflow_write = csv.writer(wfoutcsv, delimiter='\n')
        workflow_write.writerows([workflow])
    return workflow_outfile

# query data base for collections id
def assign_collections(woid):

    # get cod for woid
    admin_collections = subprocess.check_output(["wo_info", "--report", "billing", "--woid", woid]).decode(
        'utf-8').splitlines()

    collection = ''
    for ap in admin_collections:
        if 'Administration Project' in ap:
            collection = ap.split(':')[1].strip()

    return collection


while True:

    # enter woid, check to see if it doesn't exist
    woid = input('**CCDG Topup QC**\nwoid: (enter to exit)\n')

    if len(woid) == 0:
        print('Exiting cgup.py.')
        break
    if woid in woid_dirs:
        print('{} exists, please check that woid is correct.'.format(woid))
        continue

    # get collections info (from email header)
    # collection = assign_collections(woid)
    collection = 'TEST'
    print('\nAdmin Project: {}'.format(collection))

    # user input sample number
    sample_number = input('\nSample number:\n')
    qc_check = input(
        '\nQC {} with {} samples using {}? (y or enter to exit)\n'.format(woid, sample_number, collection))

    if len(qc_check) == 0:
        print('Exiting cgup.py.')
        break
    elif qc_check == 'y':
        pass
    else:
        print('Input y, no to restart or enter to exit')
        continue

    print('\nStarting QC on {} topup.\n'.format(woid))

    #mk new woid directory/chg dir
    os.makedirs(woid)
    os.chdir(woid)
    woid_dir = os.getcwd()
    print('{} dir:\n{}\n'.format(woid,woid_dir))

    # user enter lims sample info output to woid.workflow.date.tsv
    workflow_outfile =  workflow_create(woid)
    print('Samples added to {}\n'.format(workflow_outfile))

    # mk qc.samplenumber.date dir
    qc_dir = 'qc.' + sample_number + '.' + date_time
    os.makedirs(qc_dir)
    os.rename(workflow_outfile, qc_dir + '/'+ workflow_outfile)
    os.chdir(qc_dir)
    qc_dir_path = os.getcwd()
    print('{} QC directory:\n{}\n'.format(woid, qc_dir_path))


    # run qc scripts in qc dir
    ccdg_out = woid + '.' + sample_number + '.' + date_time

    # subprocess.run(["/gscuser/zskidmor/bin/python3", "/gscuser/awollam/aw/qc.build38.topmed.py", "--tm", workflow_outfile, topmed_out])
    subprocess.run(["/gscuser/zskidmor/bin/python3", "/gscuser/awollam/aw/qc.build38.ccdgnew.py", "--ccdg", workflow_outfile, ccdg_out])

    ccdg_all = woid + '.' + sample_number + '.' + date_time + '.build38.all.tsv'
    ccdg_report = woid + '.' + sample_number + '.' + date_time + '.report'
    # subprocess.run(["/gscuser/zskidmor/bin/python3", "/gscuser/awollam/aw/qc.build38.topmed.reportmaker.py", "--tm", topmed_all, topmed_report])

    # qc.build38.topmed.reportmaker.py
    qc_report = subprocess.check_output(["/gscuser/zskidmor/bin/python3",
                                         "/gscuser/awollam/aw/qc.build38.reportmaker.py", "--ccdg", ccdg_all,
                                         ccdg_report]).decode('utf-8').splitlines()

    # mk attachments dirs cp all, fail, metrics, samplemap to attachments dir
    os.makedirs('attachments')

    copyfile(ccdg_all, 'attachments/'+ccdg_all)

    ccdg_fail = ccdg_out + '.build38.fail.tsv'
    num_fail_lines = sum(1 for line in open(ccdg_fail))
    if num_fail_lines > 1:
        copyfile(ccdg_fail, 'attachments/'+ccdg_fail)

    samplemap = ccdg_out + '.qcpass.samplemap.tsv'
    num_samplemap_lines = sum(1 for line in open(samplemap))
    if num_samplemap_lines > 1:
        copyfile(samplemap, 'attachments/'+samplemap)

    os.chdir('attachments')
    att_dir = os.getcwd()
    print('\nAttachments directory:\n{}\n'.format(att_dir))

    # write correct attachment footer and scp command to file in attachments
    print('Attachments:')
    print('{} - contains all the stats for samples that have been QCed'.format(ccdg_all))
    print('{} - contains the file paths to QC passed samples'.format(samplemap))
    print('{} - contains the stats for failed samples'.format(ccdg_fail))

    # scp link
    print('\nscp link:\nscp {}@{}:{}/*.tsv .'.format(user,host,att_dir))