var socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('connect', function() {
    // we emit a connected message to let know the client that we are connected.
    socket.emit('client_connected', {data: 'New client!'});
    console.log('client_connected', {data: 'New client!'});
});

socket.on('message', function (data) {
    console.log('message from backend ' + data);
});

socket.on('alert', function (data) {
    alert('Alert Message!! ' + data);
});

var downloading = false;
var downloading_guid;

function download_video(guid) {
    if (downloading===false) {
        socket.emit('download', guid);
        downloading_guid = guid;
        downloading = true;
        document.getElementById(guid+"-progress").style.display = "inline";
        Materialize.toast('Downloading '+guid, 4000);
    } else {
        Materialize.toast('Something is already downloading, please wait until complete', 4000);
    }
}

function open_video(guid) {
    socket.emit('open_video', guid);
}

socket.on('downloading', function(data) {
    if (data < 100) {
        document.getElementById(downloading_guid+"-determinate").style.width = data + '%';
    } else if (data === 'done') {
        document.getElementById(downloading_guid+"-progress").style.display = "none";
        document.getElementById(downloading_guid+"-icon").innerText = "movie";
        Materialize.toast('Finished downloading '+downloading_guid, 4000);
        downloading = false;
    }
});


