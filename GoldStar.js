class Dog{
    constructor(){
      this.age = 47;
      this.name = "Fido";
    }
    bark(){
      var xhttp = new XMLHttpRequest();
      var that = this;
      xhttp.onreadystatechange = function() {
        if(this.readyState === 4 && this.status === 200) {
          console.log(this.responseText);
          that.age = parseInt(this.responseText);
        }//if
      }//xhttp
      xhttp.open("GET", "/ajax", true);
      xhttp.send();
    }//bark
  }//class
var dog = new Dog();
dog.bark();
console.log(dog.age);
