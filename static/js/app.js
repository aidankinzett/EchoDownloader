var socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('connect', function () {
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
    if (downloading === false) {
        socket.emit('download', guid);
        downloading_guid = guid;
        downloading = true;
        document.getElementById(guid + "-progress").style.display = "inline";
        Materialize.toast('Downloading ' + guid, 4000);
    } else {
        Materialize.toast('Something is already downloading, please wait until complete', 4000);
    }
}

function download_hq_video(guid) {
    if (downloading === false) {
        console.log('downloading in hd');
        socket.emit('download_hq', guid);
        downloading_guid = guid;
        downloading = true;
        document.getElementById(guid + "-progress").style.display = "inline";
        document.getElementById(guid + "-words").innerText = "Downloading...";
        Materialize.toast('Downloading ' + guid, 4000);
    } else {
        Materialize.toast('Something is already downloading, please wait until complete', 4000);
    }
}

function open_video(guid) {
    socket.emit('open_video', guid);
}

function mark_video_as_watched(guid) {
    socket.emit('mark_watched', guid);
    document.getElementById(guid + "-newbadge").style.visibility = "hidden";
    document.getElementById(guid + "-watched").style.display = "none";
    document.getElementById(guid + "-unwatched").style.display = "inline";

}

function mark_video_as_unwatched(guid) {
    socket.emit('mark_unwatched', guid);
    document.getElementById(guid + "-newbadge").style.visibility = "visible";
    document.getElementById(guid + "-watched").style.display = "inline";
    document.getElementById(guid + "-unwatched").style.display = "none";
}

socket.on('downloading', function (data) {
    if (data < 100) {
        document.getElementById(downloading_guid + "-determinate").style.width = data + '%';
    } else if (data === 'done') {
        document.getElementById(downloading_guid + "-progress").style.display = "none";
        document.getElementById(downloading_guid + "-icon").innerText = "movie";
        Materialize.toast('Finished downloading ' + downloading_guid, 4000);
        downloading = false;
    }
});

socket.on('downloading_hq', function (data) {
    document.getElementById(data.guid + "-progress").style.display = "inline";
    downloading = true;

    console.log(data)
    if (data.downloading < 100) {
        document.getElementById(data.guid + "-words").innerText = "Downloading...";
        document.getElementById(data.guid + "-determinate").style.width = data.downloading + '%';
    }
    if (data.downloading === 100 && data.converting < 100) {
        document.getElementById(data.guid + "-determinate").style.width = data.converting + '%';
        document.getElementById(data.guid + "-words").innerText = "Converting..."
    }
    if (data.download === 100 && data.converting === 100) {
        document.getElementById(data.guid + "-progress").style.display = "none";
        document.getElementById(data.guid + "-icon").innerText = "high-quality";
        document.getElementById(data.guid + "-words").innerText = "";
        Materialize.toast('Finished downloading ' + data.guid, 4000);
        downloading = false;
    }
});

