var socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('downloading', function (data) {
    if (data.downloading < 100) {
        document.getElementById("card1-words").innerText = "Downloading...";
        document.getElementById("card1-progress").style.width = data.downloading + '%';
        document.getElementById("card1-title").innerText = data.subject + " - " + data.title;
    } else if (data.downloading === 'done') {
        document.getElementById("card1-title").innerText = "Not Currently Downloading Anything";
        document.getElementById("card1-words").innerText =  "";
        Materialize.toast('Finished downloading ' + data.title, 4000);
    }
});

socket.on('downloading_hq', function (data) {
    if (data.downloading < 100) {
        document.getElementById("card1-title").innerText = data.subject + " - " + data.title;
        document.getElementById("card1-words").innerText = "Downloading...";
        document.getElementById("card1-progress").style.width = data.downloading + '%';
    }
    if (data.downloading === 100 && data.converting < 100) {
        document.getElementById("card1-title").innerText = data.subject + " - " + data.title;
        document.getElementById("card1-progress").style.width = data.converting + '%';
        document.getElementById("card1-words").innerText = "Converting..."
    }
    if (data.download === 100 && data.converting === 100) {
        document.getElementById("card1-title").innerText = "Not Currently Downloading Anything";
        document.getElementById("card1-words").innerText =  "";
        Materialize.toast('Finished downloading ' + data.title, 4000);
    }
});

$(document).ready(function () {
    $(".button-collapse").sideNav();
    $('.modal').modal();
});