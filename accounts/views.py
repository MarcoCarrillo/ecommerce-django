from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required

# Create your views here.
def register(request):
    form = RegistrationForm()
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            #Capturar datos
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            #Username a partir del email, traer la primer posicion del split
            username = email.split('@')[0]            
            #crear instancia de crear usuario
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email, password=password)
            user.phone_number = phone_number
            
            #Guardar usuario 
            user.save()
            
            #Alertas
            messages.success(request, 'El usuario se registró correctamente')
            return redirect('register')
            
            
    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)

def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        if email == '' or password == '':
            messages.error(request, 'Todos los campos son obligatorios')
            return redirect('login')
        
        user = auth.authenticate(email=email, password=password)
        
        if user is not None:
            auth.login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Las credenciales son incorrectas')
            return redirect('login')
            
    return render(request, 'accounts/login.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'La sesión ha finalizado')
    
    return redirect('login')