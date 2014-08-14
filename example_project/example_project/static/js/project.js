$(document).ready(function() {
	// Highlight in the navigation bar the active menu item.
	var path = window.location['pathname'];
	if (path == '/') {
		$('ul.navbar-nav li.home').addClass('active');
	} else if (path.substring(0, 20) == '/photologue/gallery/') {
		$('ul.navbar-nav li.galleries').addClass('active');
	} else if (path.substring(0, 18) == '/photologue/photo/') {
		$('ul.navbar-nav li.photos').addClass('active');
	}

//    $('.carouselle').slick({
//        lazyLoad: 'ondemand',
//        slidesToShow: 1,
//        slidesToScroll: 1,
//        arrows: false,
//        fade: true,
//        asNavFor: '.carouselle-nav'
////        slidesToShow: 3,
////        slidesToScroll: 1
//    });
//
//    $('.carouselle-nav').slick({
//        slidesToShow: 3,
//        slidesToScroll: 1,
//        asNavFor: '.carouselle',
////        dots: true,
//        centerMode: true,
//        focusOnSelect: true
//    });
});