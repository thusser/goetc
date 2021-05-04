# GoETC

Exposure time calculator for the IAG's telescope.

Download::

    git clone https://github.com/thusser/goetc.git
    cd goetc
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Run::

    python -m goetc

Use in a script::

    import astropy.units as u
    from astropy.coordinates import Angle
    from goetc.simulation import Simulation, Sky
    from goetc.config import CONFIG
    
    # init configuration
    CONFIG.init()
    
    # spectrum
    spec_bandpass = CONFIG.bandpass('Bessel/V')
    spectrum = CONFIG.spectrum('G5 III').norm_to_mag(spec_bandpass, 15.0)
    
    # get telescope/camera/bandpass/sky
    telescope = CONFIG.telescope('IAG50cm')
    camera = CONFIG.camera('SBIG STL-6303e')
    bandpass = CONFIG.bandpass('Bessel/V')
    sky = Sky()
    
    # define parameters
    binning = 1
    aper_radius = Angle(2.0 * u.arcsec)
    exp_time = 5. * u.second
    
    # calculate S/N
    sim = Simulation(telescope, camera, bandpass)
    sim.signal_to_noise(sky, spectrum, exp_time, aper_radius, binning)
    
    # print results
    print('S/N:', sim.snr)
    print('Peak count:', sim.peak)
    
