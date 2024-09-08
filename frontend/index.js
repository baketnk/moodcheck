// main.js

const App = {
    webcamStream: null,
    videoElement: null,
    captureInterval: null,
    criteria: [],
    current_goal: "Follow the instruction!",
    results: [],
    scoreText: null,
    countdown: 0,
    countdown_interval: null,

    startCapture() {
        // Request criteria from server
        this.videoElement.play();
        m.request({
            method: 'GET',
            url: 'http://localhost:3000/start'
        }).then(result => {
            this.criteria = result.goals;
            this.countdown = 3;
            this.countdown_interval = setInterval(() => {
              this.countdown -= 1;
              if (this.countdown <=0) {
                clearInterval(this.countdown_interval);
                this.countdown_interval = null;
                this.gameStart();
              }
              m.redraw();
            }, 1000);
        });
    },
    gameStart() {
            // Start capturing images
            this.current_goal = this.criteria.pop();
            this.captureInterval = setInterval(() => {
                if (this.criteria.length == 0) {
                      this.finishGame();
                      return;
                    }
                if (this.videoElement) {
                    const canvas = document.createElement('canvas');
                    canvas.width = this.videoElement.videoWidth;
                    canvas.height = this.videoElement.videoHeight;
                    canvas.getContext('2d').drawImage(this.videoElement, 0, 0);
                    
                    canvas.toBlob(blob => {
                        console.log('Blob type:', blob.type);
                        console.log("Blob len:", blob.length);
                        const formData = new FormData();
                        formData.append('image', blob);
                        formData.append('goal', this.current_goal);
                        m.request({
                            method: 'POST',
                            url: 'http://localhost:3000/submit',
                            body: formData,
                            serialize: function(value) { return value; }
                        }).then(result => {
                            console.log('Image processed:', result);
                            this.results.push(result);
                        });
                    }, 'image/jpeg');
                    if (this.criteria.length == 0) {
                      this.finishGame();
                      return;
                    }
                    this.current_goal = this.criteria.pop();
                }
            }, 5000); // Capture every 5 seconds
    },
    finishGame() {
      this.stopCapture();
      this.scoreText = JSON.stringify(this.results);
    },
    
    stopCapture() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }
        if (this.countdown_interval) {
            clearInterval(this.countdown_interval);
            this.countdown_interval = null;
        }
        this.videoElement.pause();
    },

    oninit() {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                this.webcamStream = stream;
                this.videoElement.srcObject = this.webcamStream;
            })
            .catch(error => {
                console.error('Error accessing webcam:', error);
            });
    },

    onremove() {
        this.stopCapture();
        if (this.webcamStream) {
            this.webcamStream.getTracks().forEach(track => track.stop());
        }
    },

    view() {
        return m('div', [
            m('h1', "MOODCHECK"),
            m("div", { class: "box" }, this.current_goal),
            m("div", { class: "notification is-link", style: {display: this.countdown > 0 ? "block" : "none" }}, "Starting in: "+this.countdown),
            m('video', {
                oncreate: vnode => {
                    this.videoElement = vnode.dom;

                },
                width: 640,
                height: 480,
                playsinline: true,
            }),
            m("div", { "class": "box" }, [
              m('button', { class: "button", onclick: () => this.startCapture() }, 'Start Capture'),
              m('button', { class: "button", onclick: () => this.stopCapture() }, 'Stop Capture'),
            ]),
            m("div", { "class": "box" }, this.scoreText)
        ]);
    }
};

m.mount(document.body, App);
