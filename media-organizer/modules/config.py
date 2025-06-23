import os

# Container paths - aligned with docker volumes
UNORGANIZED_DIR = '/app/media/unorganized'
DEST_DIRS = {
    'JAV': '/app/media/JAV', 
    'Shows': '/app/media/Shows', 
    'Movie': '/app/media/Movies'
}
TRACK_FILE = '/app/data/copied_files.json'

# API Keys from environment
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# JAV Prefix codes
JAV_PREFIXES = {
    'STARS', 'START', 'SDJS', 'SDMU', 'DSVR', 'SSHN', 'OKYH', 'STAR',
    'SSIS', 'SSNI', 'SNIS', 'SIVR', 'ONED', 'ONE', 'SRS',
    'MIDE', 'MIDV', 'MIDD', 'MIRD', 'MIFD', 'MIMK', 'MIAA', 'MDVR', 'MIAD', 'MIAE', 'MIAS', 'MIXS', 'MIGD', 'MIID', 'MDLD', 'MINT',
    'ABP', 'ABS', 'ABF', 'CHN', 'BGN',
    'DVAJ', 'AJVR', 'DV', 'KA',
    'WANZ', 'WAAA',
    'ADN', 'ATID', 'RBD', 'SHKD', 'JBD',
    'DASD', 'DAZD', 'DASS',
    'PPPD', 'PPPE', 'PPSD', 'PPFD', 'PPMD', 'PPUD', 'PPBD', 'PPVR',
    'AVERV', 'MDB', 'BAZX', 'BZVR', 'BMVR', 'BMVRS', 'DPVR', 'EXVR', 'HOTVR', 'KBVR', 'KMVR', 'VRKM', 'SAVR', 'SQVR', 'BOKD',
    'JUX', 'JUL', 'JUR', 'JUFD', 'JUFE',
    'IPX', 'IPZ', 'IPTD', 'IPZZ',
    'EBOD',
    'NHDTA',
    'HBAD',
    'FSDSS', 'FLNS', 'FSLV',
    'PRED',
    'MEYD',
    'JUY',
    'SPRD',
    'MVSD',
    'MXGS',
    'MXBD',
    'SDAB',
    'SDSI',
    'SDDE',
    'SDMU',
    'SDJS',
    'SDTH',
    'SDEN',
    'DOKS',
    'DOCP',
    'DOCD',
    'AVSA',
    'AVOP',
    'AVKH',
    'AVGL',
    'AVSW',
    'SERO',
    'FC2',  # FC2-PPV
    'HUNTA',
    'HUNT',
    'HMN',
    'HMJM',
    'MIZD',
    'MIDA',
    'MIDV',
    'ROYD',
    'SAME',
    'PFES',
    'GVH',
    'ALDN',
    'BF',
    'REBD',
    'MD',
    'MXBD',
    'SONE',
    'ZSD',
    'ABP'
} 