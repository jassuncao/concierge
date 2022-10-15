var button = document.getElementById('pulseButton');
//
function stage1() {
    setTimeout( () => button.disabled=false, 5000)
}

function buttonPress() {
    console.log('buttonPress');
    button.disabled=true;
    fetch('/pulse').then((r) => stage1())
}

button.onclick = buttonPress;