var user = ''
var song_locations = []
var song_names = []
var loaded_songs = []

var liked_songs = []
var playing_song = ''

var standard_playlists = []

function adjustPage(resp){
    user = resp
    document.getElementById('user_offline').hidden = resp != 'NO'
    document.getElementById('user_online').hidden = resp == 'NO'
    document.getElementById('username').innerHTML = resp
    if(resp != 'NO'){
        fetch('/liked_u{' + user + '}').then(r => r.text()).then(t => {
            if(t.length > 1)
                liked_songs = t.split(',')
            updateLikedSongs()
        })
        fetch('/isCommunicating')
    }
}

function checkLogged(){
    fetch('/amILogged').then(r => r.text()).then(resp => {adjustPage(resp)})
    fetch('/isCommunicating')
}

function gotoSignup(){
    if(user == 'NO')
        location.href = '/signup'
}

function gotoLogin(){
    if(user == 'NO')
        location.href = '/login'
}

function gotoLogout(){
    fetch('/logout_u{' + user + '}').then(r => {location.reload()})
    fetch('/isCommunicating')
    adjustPage('NO')
}

var img_array = []
var audio_array = []
var last_load_percentage = 0

function loadPercentage(){
    var i = 0
    var loaded_items = (user == '') ? (0) : (1)

    img_array = document.getElementsByTagName('img')
    audio_array = document.getElementsByTagName('audio')

    for(i = 0; i < img_array.length; i++)
        if(img_array[i].complete)
            loaded_items++
    
    for(i = 0; i < audio_array.length; i++)
        if(audio_array[i].complete || audio_array[i].innerHTML == '<source src="" type="">')
            loaded_items++
    return loaded_items / (img_array.length + audio_array.length + 1)
}

function checkLoading(){
    var check = setInterval(function () {
        var percentage = loadPercentage()
        if(percentage <= last_load_percentage && percentage < 1)
            fetch('/isCommunicating')
        else if(percentage < 1)
            last_load_percentage = percentage
        else
            clearInterval(check)
    }, 1000)
}

function createSongButtons(songs){
    var html_value = ''
    for(i = 0; i < songs.length; i++){
        var name = songs[i]
        var location = song_locations[song_names.indexOf(songs[i])]
        var onclick_fun = 'onclick=\"playAudio(\'' + name + '\',\'' + location + '\'); updateLikedSongs();\"'
        html_value += '<button class=\"music_button\"' + onclick_fun + '>' + name + '</button><br>\n'
    }
    return html_value
}

function createAlbumButtons(albums){
    var html_value = ''
    for(i = 0; i < albums.length; i++){
        var name = albums[i][0]
        var songs = albums[i].slice(1,albums[i].length)
        var onclick_fun = 'onclick=\"generatePlaylist([\'' + songs.toString().replaceAll(',','\',\'') + '\'])\"'
        html_value += '<button class=\"album_button\"' + onclick_fun + '>' + name + '</button><br>\n'
    }
    return html_value
}

function findSongsWithSearch(){
    var words = document.getElementById('search_text').value.toLowerCase()
    var word_count = document.getElementById('search_text').value.toLowerCase().split(' ').length
    var matching_song_locations = []
    var matching_song_names = []
    var i, j, k, kind
    var song = ''

    if(words == ''){
        document.getElementById('search_results').innerHTML = ''
        return
    }
    
    for(i = 0; i < song_names.length; i++){
        song = song_names[i].toLowerCase()
        var song_parts = song.split(' ').filter(e => e !== ' ')
        var song_name_parts = [] // Começa com o nome da música
        var band_name_parts = [] // Começa com o nome da banda
        var fraction = []
        var band = false
        var found = false
        
        // Adquirindo nome da música e da banda
        for(j = 0; j < song_parts.length; j++){
            if(song_parts[j] == '-')
                band = true
            else if(band == false)
                song_name_parts.push(song_parts[j])
            else
                band_name_parts.push(song_parts[j])
        }
        song_name_parts = song_name_parts.concat(band_name_parts)
        band_name_parts = band_name_parts.concat(song_name_parts)
        
        // Buscando as correspondências entre pesquisa e músicas
        for(kind = 0; kind < 2; kind++){
            var word_order = (kind == 0) ? (song_name_parts) : (band_name_parts)
            if(word_count == 1){
                for(j = 0; j < word_order.length; j++){
                    if(word_order[j].startsWith(words.split(' ')[0])){
                        matching_song_names.push(song_names[i])
                        matching_song_locations.push(song_locations[i])
                        found = true
                        break
                    }
                }
                if(found)
                    break
            } else if(word_count > 1){
                for(j = 0; j < word_order.length; j++){
                    fraction = []
                    for(k = j; k < word_order.length; k++)
                        fraction.push(word_order[k])
                    fraction = fraction.toString().replaceAll(',',' ')
                    if(fraction.startsWith(words)){
                        matching_song_names.push(song_names[i])
                        matching_song_locations.push(song_locations[i])
                        found = true
                        break
                    }
                }
                if(found)
                    break
            }
        }
    }
    // Mostrando para o usuário
    document.getElementById('search_results').innerHTML = createSongButtons(matching_song_names)
}

function playAudio(name, location){
    // Checa se o áudio já foi baixado
    var contains_song = loaded_songs.includes(name)
    
    // Se o áudio não foi baixado ainda será feita uma solicitação
    if(!contains_song){
        // Criando novo elemento de áudio caso necessário
        var default_audio = document.getElementById('music_player')
        if(default_audio == null){
            var new_audio = '<audio id=\"music_player\" title=\"\" controls preload=\"auto\" autoplay><source src=\"\" type=\"\"></audio>'
            document.getElementById('loaded_music_players').innerHTML += new_audio
        }
        // Definindo atributos do áudio
        default_audio = document.getElementById('music_player')
        default_audio.id = name
        default_audio.title = name
        default_audio.src = location
        default_audio.preload = 'auto'
        default_audio.autoplay = true
        default_audio.controls = true
        loaded_songs.push(name)
        // Carregando o arquivo
        document.getElementById(name).load()
        fetch('/isCommunicating')
        last_load_percentage = 0
        checkLoading()
    }

    // Pausa todos os áudios menos o da música escolhida
    var i = 0
    for(i = 0; i < loaded_songs.length; i++){
        var song = document.getElementById(loaded_songs[i])
        if(name == loaded_songs[i]){
            playing_song = name
            if(song.paused){
                song.currentTime = 0
                song.play()
            }
            song.hidden = false
        } else {
            song.currentTime = 0
            song.pause()
            song.hidden = true
        }
    }
}

// Pausa os áudios ao sair da página
window.onbeforeunload = function (e) {
    for(i = 0; i < loaded_songs.length; i++){
        var song = document.getElementById(loaded_songs[i])
        song.pause()
    }
}

function updateLikedSongs(){
    if(playing_song != '')
        if(user != '' && user != 'NO')
            document.getElementById('like').innerHTML = (liked_songs.includes(playing_song)) ? ('Dislike') : ('Like')
    document.getElementById('liked_songs').innerHTML = createSongButtons(liked_songs)
}

function likeSong(){
    if(playing_song != ''){
        if(user != '' && user != 'NO'){
            if(liked_songs.includes(playing_song)){
                liked_songs = liked_songs.filter(d => d != playing_song)
                fetch('/dislike_u{' + user + '}s{' + playing_song + '}')
            } else {
                liked_songs.push(playing_song)
                fetch('/like_u{' + user + '}s{' + playing_song + '}')
            }
            fetch('/isCommunicating')
        }
        updateLikedSongs()
    }
}

function offlineFunctionality(){
    document.getElementById('albums_screen').innerHTML = createAlbumButtons(standard_playlists)
    //var i = 0
    //for(i = 0; i < standard_playlists.length; i++){}
}

function generatePlaylist(songs){
    document.getElementById('current_playlist').innerHTML = createSongButtons(songs)
}

////////////////////////////////////////////////////////eof
////////////////////////////////////////////////////////eof
////////////////////////////////////////////////////////eof
////////////////////////////////////////////////////////eof
////////////////////////////////////////////////////////eof