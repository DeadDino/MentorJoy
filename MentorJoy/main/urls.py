from django.urls import path
from . import views
urlpatterns = [
	path('', views.index, name='index'),
	path('login', views.login, name='login'),
	path('templates', views.templates, name='templates'),
	path('signup', views.signup, name='signup'),
	path('logout', views.logout, name='logout'),
	path('new-project', views.new_project, name='new-project'),
	path('files', views.files, name='files')
]