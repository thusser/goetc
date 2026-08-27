let app = new Vue({
    el: '#app',
    data: {
        config: {},
        target: {
            template: 'G5 V',
            magnitude: 15.0,
            bandpass: 'Bessel/V'
        },
        sky: {
            magnitude: 22.0,
            seeing: 1.0,
            airmass: 2.0,
            extinction: 0.2
        },
        telescope: {
            name: null,
            aperture: null,
            focal_length: null,
            reflectivity: null,
            obscuration: null
        },
        camera: {
            name: null,
            pixel_size: null,
            readout_noise: null,
            dark_current: null,
            gain: null,
            bias: null,
            qe: null
        },
        simulation: {
            bandpass: 'Bessel/V',
            aper_radius: 4,
            exp_time: 5.0,
            binning: 1,
        },
        results: {
            snr: null,
            peak: null,
            target: null,
            dark: null,
            sky: null,
            peak_e: null,
            target_e: null,
            dark_e: null,
            sky_e: null
        }
    },
    watch: {
        'telescope.name': function (new_tel, old_tel) {
            axios.get('/telescope/' + new_tel).then(response => {
                this.set_telescope(response.data);
            });
        },
        'camera.name': function (new_cam, old_cam) {
            axios.get('/camera/' + new_cam).then(response => {
                this.set_camera(response.data, this.simulation.binning);
            });
        },
        'simulation.binning': function (new_bin, old_bin) {
            axios.get('/camera/' + this.camera.name).then(response => {
                this.set_camera(response.data, new_bin);
            });
        }
    },
    created() {
        this.get_configs();
    },
    methods: {
        get_configs() {
            axios.get('/config').then(response => {
                this.config = response.data;
                this.telescope.name = this.config.telescopes[0];
                this.camera.name = this.config.cameras[0];
            });
        },
        set_telescope(telescope) {
            this.telescope.aperture = telescope.aperture;
            this.telescope.focal_length = telescope.focal_length;
            this.telescope.reflectivity = telescope.reflectivity;
            this.telescope.obscuration = telescope.obscuration;
        },
        set_camera(camera, binning) {
            this.camera.pixel_size = camera.pixel_size;
            this.camera.readout_noise = camera.readout_noise;
            this.camera.dark_current = camera.dark_current;
            this.camera.gain = Array.isArray(camera.gain) ? camera.gain[binning - 1] : camera.gain;
            this.camera.bias = Array.isArray(camera.bias) ? camera.bias[binning - 1] : camera.bias;
            this.camera.qe = camera.qe;
        },
        signal_to_noise() {
            axios.post('/snr', {
                telescope: this.telescope,
                camera: this.camera,
                sky: this.sky,
                sim: this.simulation,
                target: this.target
            }).then(response => {
                const r = response.data;
                this.results.snr = r.snr;
                this.results.peak = r.peak;
                this.results.target = r.target;
                this.results.dark = r.dark;
                this.results.sky = r.sky;
                // electron equivalents of the ADU counts
                this.results.peak_e = r.peak * r.gain;
                this.results.target_e = r.target * r.gain;
                this.results.dark_e = r.dark * r.gain;
                this.results.sky_e = r.sky * r.gain;
            });
            return false;
        }
    }
})