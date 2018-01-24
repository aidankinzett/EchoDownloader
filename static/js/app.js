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
    socket.emit('download', guid);
    downloading_guid = guid;
    downloading = true;
    document.getElementById(guid + "-progress").style.display = "inline";
    Materialize.toast('Downloading ' + guid, 4000);

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
    document.getElementById(data.guid + "-progress").style.display = "inline";
    downloading = true;

    if (data.downloading < 100) {
        document.getElementById(data.guid + "-words").innerText = "Downloading...";
        document.getElementById(data.guid + "-determinate").style.width = data.downloading + '%';
    } else if (data.downloading === 'done') {
        document.getElementById(data.guid + "-progress").style.display = "none";
        document.getElementById(data.guid + "-icon").innerText = "movie";
        Materialize.toast('Finished downloading ' + data.guid, 4000);
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

function add_settings_row() {
    rss_form_number += 1
    document.getElementById('rows').innerHTML += '<div class="row" id="row_' + rss_form_number + '">\n' +
        '                        <div class="input-field col s2">\n' +
        '                            <input type="text" placeholder="Subject Code" name="code_' + rss_form_number + '">\n' +
        '                        </div>\n' +
        '                        <div class="input-field col s5">\n' +
        '                            <input type="text" placeholder="RSS URL" name="rss_' + rss_form_number + '">\n' +
        '                        </div>\n' +
        "                    <div class=\"col s2\">\n" +
        "                        <p>\n" +
        "                            <input type=\"checkbox\" id=\"auto_" + rss_form_number + "\" onchange=\"activate_settings_checkbox(this, " + rss_form_number + ")\"/>\n" +
        "                            <label for=\"auto_" + rss_form_number + "\">Auto Download</label>\n" +
        "                        </p>\n" +
        "                    </div>\n" +
        "                    <div class=\"col s2\">\n" +
        "                        <p>\n" +
        "                            <input type=\"checkbox\" id=\"hq_" + rss_form_number + "\" disabled=\"disabled\" onchange=\"activate_text_hq(this, " + rss_form_number + ")\" />\n" +
        "                            <label for=\"hq_" + rss_form_number + "\">High Quality</label>\n" +
        "                        </p>\n" +
        "                   <div style=\"display: none;\">\n" +
        "                        <input id=\"text_auto_" + rss_form_number + "\" name=\"auto_" + rss_form_number + "\" value=\"off\">\n" +
        "                        <input id=\"text_hq_" + rss_form_number + "\" name=\"hq_" + rss_form_number + "\" value=\"off\">\n" +
        "                    </div>" +
        "                    </div>\n" +
        '                        <div class="delete col s1">\n' +
        '                            <a class="waves-effect waves-light btn" onclick="delete_settings_row(' + rss_form_number + ')">-</a>\n' +
        '                        </div>\n' +
        '                    </div>'
}


function delete_settings_row(row_number) {
    document.getElementById('row_' + row_number).remove();
}

function activate_settings_checkbox(checkboxElem, number) {
    if (checkboxElem.checked) {
        document.getElementById('hq_' + number).disabled = false;
        document.getElementById('text_auto_' + number).value = "on";
    } else {
        document.getElementById('hq_' + number).disabled = true;
        document.getElementById('hq_' + number).checked = false;
        document.getElementById('text_auto_' + number).value = "off";
        document.getElementById('text_hq_' + number).value = "off";
    }
}

function activate_text_hq(checkboxElem, number) {
    if (checkboxElem.checked) {
        document.getElementById('text_hq_' + number).value = "on";
    } else {
        document.getElementById('text_hq_' + number).value = "off";
    }
}

$(document).ready(function () {
    $(".button-collapse").sideNav();
    $('.modal').modal();
});