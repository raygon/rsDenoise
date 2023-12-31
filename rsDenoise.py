import pdb as ipdb

import sys, argparse
sys.path.append('/Shared/klie/data/code/rsDenoise/')
from fmriprep_helpers import *

### Set parameters #################################################
# config is a global variable used by several functions

# Where does the data live?
config.sourceDir = '/Shared/klie/data/code/rsDenoise/' # or replace with path to source code

# Processing options
config.preprocessing = 'freesurfer' 
config.interpolation = 'linear' # 'linear' or 'astropy' 'power'

# Other options
config.queue = False
config.sgeopts = '-l mem_free=25G -pe openmp 6 -q long.q'
config.overwrite = False

# interpolate over non-contiguous voxels
config.n_contiguous = 1 # 1 does not interpolate over timepoint e.g 5 

#####################################################################

def _hook_set_surface_filename_convention(args):
  """
  NEW/FCA: sub-DK0001_task-rest_run-1_{hemi-L_space-fsaverage6}_bold.func.gii
  OLD/ABIDE: sub-DK0001_task-rest_run-1_space-{fsaverage6_hemi-R}_bold.func.gii
  """
  if isinstance(args.surface, str):
    args.surface = [args.surface,]
  else:
    pass

  def _parse_surface_filename(surface_filename):
    x_split = surface_filename.split('_')
    x_parsed = {'hemi': None, 'space':[]}
    for x in x_split:
      if x.lower().startswith('hemi'):
        x_parsed['hemi'] = x
      else: #TODO: are these the only two fields that can occur in the string?
        x_parsed['space'].append(x)
    x_parsed['space'] = '_'.join(x_parsed['space'])
    return x_parsed
  surface_parsed = [_parse_surface_filename(x) for x in args.surface]

  surf_template_new = "{hemi}_space-{space}"
  surf_template_old = "space-{space}_{hemi}"
  # dict([x.split('-') for x in 'space-fsaverage6_hemi-R'.split('_')])

  # ipdb.set_trace()

  # USE_NEW_SURFACE_FORMAT = False
  USE_NEW_SURFACE_FORMAT = args.use_new_surface_format
  surface_format = '<NEW_FORMAT (FCA)>' if USE_NEW_SURFACE_FORMAT else '<OLD_FORMAT (ABIDE)>'
  out = []
  for x in surface_parsed:
    print('\t', x)
    if USE_NEW_SURFACE_FORMAT:
      surface_filename = surf_template_new.format(**x)
    else:
      surface_filename = surf_template_old.format(**x)
    out.append(surface_filename)
  print(f"FORMATTED SURFACE FILENAME AS {surface_format} -->\n\t{out}")
  return out


def main():
  parser = create_parser()
  args = parser.parse_args()

  config.DATADIR = args.datadir
  config.outDir = args.output
  config.isCifti = args.cifti
  config.isGifti = args.gifti
  config.space = args.space
  config.smoothing = args.smoothing
  config.parcellationName = args.parcellationName
  config.nParcels = args.nParcels
  config.overwrite = args.overwrite
  vFC = args.vFC

  ### <raygon: Aug 2, 2023; normalize surface input across fmriprep versions>
  surface_formatted = _hook_set_surface_filename_convention(args)
  args.surface = surface_formatted
  ### </raygon: Aug 2, 2023; normalize surface input across fmriprep versions>

  ### <raygon: Aug 2, 2023; extend to csv formatted subject file>
  try:  # load from file
    subjects = np.loadtxt(args.input,dtype=str,ndmin=1)  # paola
    if args.input.endswith('.csv'):  # raygon
      subjects = subjects[1:]
  except IOError as e: # interpret the input as a single subject ID
    subjects = [args.input,]
  # ipdb.set_trace()
  ### </raygon: Aug 2, 2023; extend to csv formatted subject file>
  if not 'sub-' in subjects[0]: subjects = np.array(['sub-' + s for s in subjects])
  config.pipelineName      = args.pipeline 
  config.Operations        = config.operationDict[config.pipelineName]
 
  # fmriRuns = ['task-rest_acq-pedj_run-1'] if 'ONRC' in config.DATADIR else ['task-rest_run-1']
  fmriRuns = ['task-rest_acq-pedj_run-1'] if 'ONRC' in config.DATADIR else ['task-rest_run-1', 'task-rest_run-2', 'task-rest_run-3', 'task-rest_run-4', 'task-rest_run-5']

  if args.seedFolder is not None: # Compute seed FC
    if config.isCifti or config.isGifti:
      for config.subject in subjects:
        args.seedFolder = args.seedFolder.replace('#subjectID#',config.subject)
        iSurf = 0
        for config.surface in args.surface:
          if len(args.parcellationFile) > 0:
            config.parcellationFile = args.parcellationFile[iSurf]
            config.parcellationFile = config.parcellationFile.replace('#subjectID#',config.subject)
            sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
            if 'ONRC' in config.DATADIR: sessions = ['ses-1']
            if len(sessions) > 0:
              for config.session in sessions:
                for config.fmriRun in fmriRuns:
                  print('Processing:',config.subject, config.session, config.fmriRun, flush=True)
                  seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
                  for seedFile in seeds:
                    #print('seed:',seedFile)
                    if args.FCdir is None:
                      config.FCDir = op.join(config.outDir,config.pipelineName+'_{}_{}_seedFC'.format(config.space,op.splitext(op.basename(seedFile))[0]))
                    else:
                      config.FCDir = args.FCdir
                    runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=False)
            else: # no sessions
              if hasattr(config,'session'): delattr(config,'session')
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.fmriRun)
                seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
                for seedFile in seeds:
                  #print('seed:',seedFile)
                  if args.FCdir is None:
                    config.FCDir = op.join(config.outDir,config.pipelineName+'_{}_{}_seedFC'.format(config.space,op.splitext(op.basename(seedFile))[0])) 
                  else:
                    config.FCDir = args.FCdir               
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=False)
          else: # compute seed to vertex FC
            sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
            if 'ONRC' in config.DATADIR: sessions = ['ses-1']
            if len(sessions) > 0:
              for config.session in sessions:
                for config.fmriRun in fmriRuns:
                  print('Processing:',config.subject, config.session, config.fmriRun)
                  seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
                  for seedFile in seeds:
                    #print('seed:',seedFile)
                    if args.FCdir is None:
                      config.FCDir = op.join(config.outDir,config.pipelineName+'_{}_{}_seedFC'.format(config.space,op.splitext(op.basename(seedFile))[0]))
                    else:
                      config.FCDir = args.FCdir
                    runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=True)
            else: # no sessions
              if hasattr(config,'session'): delattr(config,'session')
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.fmriRun)
                seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
                for seedFile in seeds:
                  #print('seed:',seedFile)
                  if args.FCdir is None:
                    config.FCDir = op.join(config.outDir,config.pipelineName+'_{}_{}_seedFC'.format(config.space,op.splitext(op.basename(seedFile))[0])) 
                  else:
                    config.FCDir = args.FCdir               
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=True)
          iSurf = iSurf + 1
        args.seedFolder = args.seedFolder.replace(config.subject,'#subjectID#')      
    else: # process nifti files
      if len(args.parcellationFile) > 0:
        for config.subject in subjects:
          config.parcellationFile = args.parcellationFile[0]
          config.parcellationFile = config.parcellationFile.replace('#subjectID#',config.subject)
          args.seedFolder = args.seedFolder.replace('#subjectID#',config.subject)
          sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
          if 'ONRC' in config.DATADIR: sessions = ['ses-1']
          if len(sessions) > 0:
            for config.session in sessions:
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.session, config.fmriRun)
                seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
                for seedFile in seeds:
                  #print('seed:',seedFile)
                  if args.FCdir is None:
                    config.FCDir = op.join(config.outDir,config.pipelineName+'_{}_{}_seedFC'.format(config.space,op.splitext(op.basename(seedFile))[0]))
                  else:
                    config.FCDir = args.FCdir
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=False)
          else: # no sessions
            if hasattr(config,'session'): delattr(config,'session')
            for config.fmriRun in fmriRuns:
              print('Processing:',config.subject, config.fmriRun)
              seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
              for seedFile in seeds:
                #print('seed:',seedFile)
                if args.FCdir is None:
                  config.FCDir = op.join(config.outDir,config.pipelineName+'_{}_{}_seedFC'.format(config.space,op.splitext(op.basename(seedFile))[0]))   
                else:
                  config.FCDir = args.FCdir               
                runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=False)
          args.seedFolder = args.seedFolder.replace(config.subject,'#subjectID#')      
      else: # compute seed to voxel FC
        for config.subject in subjects:
          args.seedFolder = args.seedFolder.replace('#subjectID#',config.subject)
          sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
          if 'ONRC' in config.DATADIR: sessions = ['ses-1']
          if len(sessions) > 0:
            for config.session in sessions:
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.session, config.fmriRun)
                seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
                for seedFile in seeds:
                  #print('seed:',seedFile)
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=True)
          else: # no sessions
            if hasattr(config,'session'): delattr(config,'session')
            for config.fmriRun in fmriRuns:
              print('Processing:',config.subject, config.fmriRun)
              seeds = [op.join(args.seedFolder,config.space,fpath) for fpath in os.listdir(op.join(args.seedFolder,config.space))]
              for seedFile in seeds:
                #print('seed:',seedFile)
                runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=seedFile,vFC=True)
          args.seedFolder = args.seedFolder.replace(config.subject,'#subjectID#')
  else: # compute either parcel-to-parcel or voxel/vertex-wise whole brain FC (or skip FC)
    if config.isCifti or config.isGifti:
      if len(args.parcellationFile) > 0:
        if args.FCdir is None:
          config.FCDir = op.join(config.outDir,config.pipelineName+'_surf_FC')
        else:
          config.FCDir = args.FCdir 
        for config.subject in subjects: 
          iSurf = 0
          for config.surface in args.surface:
            config.parcellationFile = args.parcellationFile[iSurf]
            config.parcellationFile = config.parcellationFile.replace('#subjectID#',config.subject)
            sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
            if 'ONRC' in config.DATADIR: sessions = ['ses-1']
            if len(sessions) > 0:
              for config.session in sessions:
                for config.fmriRun in fmriRuns:
                  print('Processing:',config.subject, config.session, config.fmriRun)
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=False)
            else:
              if hasattr(config,'session'): delattr(config,'session')
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.fmriRun)
                runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=False)
            iSurf = iSurf + 1
      else: # no parcellation file provided
        for config.subject in subjects: 
          iSurf = 0
          for config.surface in args.surface:
            sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
            if 'ONRC' in config.DATADIR: sessions = ['ses-1']
            if len(sessions) > 0:
              for config.session in sessions:
                for config.fmriRun in fmriRuns:
                  print('Processing:',config.subject, config.session, config.fmriRun)
                  if vFC:
                    runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=True)
                  else:
                    runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=False)
            else: # no sessions
              if hasattr(config,'session'): delattr(config,'session')
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.fmriRun)
                if vFC:
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=True)
                else:
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=False)
            iSurf = iSurf + 1
    else: # process nifti files
      if len(args.parcellationFile) > 0:
        if args.FCdir is None:
          config.FCDir = op.join(config.outDir,config.pipelineName+'_vol_FC')
        else:
          config.FCDir = args.FCdir 
        for config.subject in subjects:
          config.parcellationFile = args.parcellationFile[0]
          config.parcellationFile = config.parcellationFile.replace('#subjectID#',config.subject)
          sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
          if 'ONRC' in config.DATADIR: sessions = ['ses-1']
          if len(sessions) > 0:
            for config.session in sessions:
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.session, config.fmriRun)
                runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=False)
          else: # no sessions
            if hasattr(config,'session'): delattr(config,'session')
            for config.fmriRun in fmriRuns:
              print('Processing:',config.subject, config.fmriRun)
              runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=False)    
      else: # no parcellation file provided
        for config.subject in subjects:
          sessions = [fpath for fpath in os.listdir(op.join(config.DATADIR,'fmriprep',config.subject)) if fpath.startswith('ses-')]
          if 'ONRC' in config.DATADIR: sessions = ['ses-1']
          if len(sessions) > 0:
            for config.session in sessions:
              for config.fmriRun in fmriRuns:
                print('Processing:',config.subject, config.session, config.fmriRun)
                if vFC:
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=True)
                else:
                  runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=False)
          else: # no sessions
            if hasattr(config,'session'): delattr(config,'session')
            for config.fmriRun in fmriRuns:
              print('Processing:',config.subject, config.fmriRun)
              if vFC:
                runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=True,seed=None,vFC=True)
              else:
                runPipelinePar(overwriteFC=True,do_makeGrayPlot=True,do_computeFC=False)
  # launch array job (if there is something to do)
  if len(config.scriptlist)>0:
    JobID = fnSubmitJobArrayFromJobList()
    config.joblist.append(JobID.split(b'.')[0])
    checkProgress(pause=60,verbose=False)


def create_parser():
  parser = argparse.ArgumentParser(description='Launch rsDenoise pipeline.')
  parser.add_argument('-space', '--space', metavar='SPACE', type=str,
              default='MNI152NLin6Asym_res-2', help="""Space for volumetric data or volumetric seed.""")
  parser.add_argument('-surf', '--surface', metavar='SURFACE', type=str, nargs='+',
            default=['fsaverage6_hemi-L','fsaverage6_hemi-R'], help="""Space for surface data. More than one space can be specified.""")

  parser.add_argument('-use_new_surface_format', '--use_new_surface_format', action='store_true', default=False,
            help="""Hack to switch surface filename convention for fmriprep.""")

  parser.add_argument('-parcelName', '--parcellationName', metavar='PARCELLATION_NAME', type=str,
            default=None, help="""Parcellation name, used in output file names. Only required for parcel-wise FC. 
            To be specified together with -parcelFile and -parcelName""")
  parser.add_argument('-parcelFile', '--parcellationFile', metavar='PARCELLATION_FILE', type=str, nargs='+',
            default=[], help="""Path(s) to parcellation file. More than one can be specified, but they need
            to match order and number of surfaces. Only required for parcel-wise FC. To be specified together with -parcelFile and -parcelName""")
  parser.add_argument('-n', '--nParcels', metavar='N_PARCELS', type=int,
            default=None, help="""Number of parcels in parcellation. Only required for parcel-wise FC. To be specified together with -parcelFile and -parcelName""")
  parser.add_argument('-vFC', '--vFC', action='store_true', default=False,
            help="""Compute vertex- or voxel-wise connectivity""")
  parser.add_argument('-seed', '--seedFolder', metavar='FILE', type=str,
            help="""Folder where seeds are stored. Only required for seed FC.""")
  parser.add_argument('-FCdir', '--FCdir', metavar='FOLDER', type=str,
            default=None, help="""Folder where to store FC outputs for all subjects.""")
  parser.add_argument('-gifti', '--gifti', action='store_true', default=False,
            help="""Process gifti surface data.""") 
  parser.add_argument('-cifti', '--cifti', action='store_true', default=False,
            help="""Process cifti volumetric data.""")  
  parser.add_argument('-smooth', '--smoothing', metavar='FWHM', type=float,
            default=None, help="""To request smoothing, specify FWHM in mm.""")
  parser.add_argument('-overwrite', '--overwrite', action='store_true', default=False,
            help="""Overwrite previous outputs""")
  requiredNamed = parser.add_argument_group('required named arguments')
  requiredNamed.add_argument('-data', '--datadir', metavar='FOLDER', type=str,
                 help="""Folder where subject data is be stored.""", required=True)
  requiredNamed.add_argument('-i', '--input', metavar='FILE', type=str,
                 help="""File containing list of subject IDs to process.""", required=True)
  requiredNamed.add_argument('-pipe', '--pipeline', metavar='NAME', type=str,
                 help="""Name of denoising pipeline to apply.""", required=True)
  requiredNamed.add_argument('-o', '--output', metavar='FOLDER', type=str,
                 help="""Folder where outputs will be stored.""", required=True)
  return parser

  

if __name__ == "__main__":
  main()


