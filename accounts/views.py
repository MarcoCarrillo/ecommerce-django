from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegistrationForm, UserProfileForm, UserForm
from .models import Account, UserProfile
from orders.models import Order
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage

from carts.views import _cart_id
from carts.models import Cart, CartItem

import requests
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
            
            
            profile = UserProfile()
            profile.user_id = user.id
            profile.profile_picture = 'default/default-user.png'
            profile.save()
            
            
            #Activacion de cuenta por correo
            current_site = get_current_site(request)
            mail_subject = 'Activacion de cuenta Ecommerce'
            body = render_to_string('accounts/account_verification_email.html', {
                'user' : user,
                'domain' : current_site,
                'uid' : urlsafe_base64_encode(force_bytes(user.pk)), #Cifrar id hexadefimal
                'token' : default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, body, to=[to_email])
            send_email.send()
                        
            #Alertas
            
            return redirect('/accounts/login/?command=verification&email='+email)
            
            
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
        
        #Si el usuario pudo iniciar sesion
        if user is not None:
            #Si el usuario no esta logueado y agrega un item al carrito asignarle lo que tenga en el carrito cuando inicie sesion
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)
                    
                    #Verificar variations de los items cuando no estaba en sesion y cuando si
                    product_variation = []
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variation.append(list(variation))
                        
                    cart_item = CartItem.objects.filter(user=user)
                    ex_var_list = []
                    id = []
                    for item in cart_item:
                        existing_variation = item.variations.all()
                        ex_var_list.append(list(existing_variation)) 
                        id.append(item.id)
                    
                    for pr in product_variation:
                        if pr in ex_var_list:
                            index = ex_var_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart) 
                            for item in cart_item:
                                item.user = user
                                item.save()                  
                                        
            except:
                pass
                    
                    
            #http://localhost:8000/accounts/login/?next=/cart/checkout/    
            auth.login(request, user)
            messages.success(request, 'Has iniciado sesion correctamente')
            
            url = request.META.get('HTTP_REFERER') #Capturar url
            try:
                query = requests.utils.urlparse(url).query
                #next=/cart/checkout/
                params = dict(x.split('=') for x in query.split('&'))
                
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('dashboard')

            return redirect('dashboard')
        else:
            messages.error(request, 'Las credenciales son incorrectas')
            return redirect('login')
            
    return render(request, 'accounts/login.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'La sesión ha finalizado')
    
    return redirect('login')


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None 
        
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Tu cuenta ha sido activada correctamente')
        return redirect('login')
    else: 
        messages.error(request, 'Ups! Hubo un error de activacion')
        return redirect('register')
    

@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()
    context = {
        'orders_count': orders_count,
    }
    return render(request, 'accounts/dashboard.html', context)
    
    
def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            
            current_site = get_current_site(request)
            mail_subject = 'Recupera tu contraseña'
            body = render_to_string('accounts/reset_password_email.html', {
                'user' : user,
                'domain' : current_site,
                'uid' : urlsafe_base64_encode(force_bytes(user.pk)),
                'token' : default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, body, to=[to_email])
            send_email.send()

            messages.success(request, 'Se te envio un correo electronico para reestablecer tu contraseña!')
            return redirect('login')
        else:
            messages.error(request, 'Ups! La cuenta de usuario no existe!')
            return render(request, 'accounts/forgotPassword.html')

    return render(request, 'accounts/forgotPassword.html')

def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Por favor, ingresa una nueva contraseña')
        return redirect('resetPassword')
    else:
        messages.error(request, 'El link ha expirado')    
        
        
def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'La contraseña se ha restablecido correctamente!')
            return redirect('login')
        else:
            messages.error(request, 'Las contraseñas ingresadas no son iguales')
            return redirect('resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')
            
                        
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    context = {
        'orders': orders,
    }
    
    return render(request, 'accounts/my_orders.html', context)


def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile) 
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Su informacion fue guardada con exito') 
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
        
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'userprofile': userprofile,
    }
    
    return render(request, 'accounts/edit_profile.html', context)          
