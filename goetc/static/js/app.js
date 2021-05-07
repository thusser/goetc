let app = new Vue({
    el: '#app',
    data: {
        config: {},
        target: {
            template: 'G5 V',
            mag: 15.0,
            bandpass: 'Bessel/V'
        },
        sky: {
            mag: 22.0,
            seeing: 1.0,
            airmass: 2.0,
            extinction: 0.2
        },
        telescope: {
            preset: null,
            aperture: null,
            focal_length: null,
            reflectivity: null,
            obscuration: null
        },
        camera: {
            preset: null,
            binning: 1,
            pixel_size: null,
            readout_noise: null,
            dark_current: null,
            gain: null,
            bias: null,
            qe: null
        },
        simulation: {
            bandpass: 'Bessel/V',
            aperture: 4,
            exp_time: 5.0
        }
    },
    watch: {
        'telescope.preset': function (new_tel, old_tel) {
            axios.get('/telescope/' + new_tel).then(response => {
                this.set_telescope(response.data);
            });
        },
        'camera.preset': function (new_cam, old_cam) {
            axios.get('/camera/' + new_cam).then(response => {
                this.set_camera(response.data, this.camera.binning);
            });
        },
        'camera.binning': function (new_bin, old_bin) {
            axios.get('/camera/' + this.camera.preset).then(response => {
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
                this.telescope.preset = this.config.telescopes[0];
                this.camera.preset = this.config.cameras[0];
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
        }
    }
})