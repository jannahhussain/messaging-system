// Handle notifications dropdown
document.addEventListener('DOMContentLoaded', function() {
    const notificationButton = document.getElementById('notificationButton');
    const notificationDropdown = document.getElementById('notificationDropdown');

    if (notificationButton) {
        notificationButton.addEventListener('click', function(event) {
            event.stopPropagation();
            notificationDropdown.classList.toggle('show');
        });
    }

    window.addEventListener('click', function() {
        if (notificationDropdown) {
            notificationDropdown.classList.remove('show');
        }
    });

    // Handle loading more messages on scroll to top
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.addEventListener('scroll', function() {
            if (chatMessages.scrollTop === 0) {
                loadMoreMessages();
            }
        });
    }
});

// Load more chat messages (stub to replace with actual backend call later)
function loadMoreMessages() {
    console.log('Loading more messages...');
    // You would fetch('/load_messages') here and prepend messages
}

// Handle flagging messages
function flagMessage(messageId) {
    fetch(`/flag_message/${messageId}`, {
        method: 'POST'
    })
    .then(response => {
        if (response.ok) {
            alert('Message flagged for admin review.');
        } else {
            alert('Error flagging message.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Search for users
function searchUser() {
    const searchInput = document.getElementById('searchInput').value.trim();
    const searchResults = document.getElementById('searchResults');

    if (searchInput.length === 0) {
        searchResults.innerHTML = '<p>Please enter a username.</p>';
        return;
    }

    fetch(`/search_user?username=${encodeURIComponent(searchInput)}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            searchResults.innerHTML = `<p>User found: ${data.user.full_name}</p>`;
            // Add connect/decline button if needed
        } else {
            searchResults.innerHTML = `<p>${data.message}</p>`;
        }
    })
    .catch(error => {
        searchResults.innerHTML = '<p>Error searching for user.</p>';
    });
}

// Validate Register Form
function validateRegisterForm() {
    const firstName = document.forms['registerForm']['first_name'].value.trim();
    const lastName = document.forms['registerForm']['last_name'].value.trim();
    const email = document.forms['registerForm']['email'].value.trim();
    const password = document.forms['registerForm']['password'].value.trim();
    const securityAnswer = document.forms['registerForm']['security_answer'].value.trim();

    if (!firstName || !lastName || !email || !password || !securityAnswer) {
        alert('Please fill in all fields.');
        return false;
    }
    return true;
}

// Validate Forgot Password Form
function validateForgotPasswordForm() {
    const thirdLetter = document.forms['forgotPasswordForm']['third_letter'].value.trim();
    const email = document.forms['forgotPasswordForm']['email'].value.trim();
    const securityAnswer = document.forms['forgotPasswordForm']['security_answer'].value.trim();

    if (!thirdLetter || !email || !securityAnswer) {
        alert('Please fill in all fields.');
        return false;
    }
    return true;
}

// Profile Actions for Admin
function banUser(userId) {
    if (confirm('Are you sure you want to ban this user?')) {
        fetch(`/admin/ban_user/${userId}`, { method: 'POST' })
        .then(response => {
            if (response.ok) {
                alert('User has been banned.');
                window.location.reload();
            } else {
                alert('Failed to ban user.');
            }
        });
    }
}

function suspendUser(userId) {
    if (confirm('Are you sure you want to suspend this user?')) {
        fetch(`/admin/suspend_user/${userId}`, { method: 'POST' })
        .then(response => {
            if (response.ok) {
                alert('User has been suspended.');
                window.location.reload();
            } else {
                alert('Failed to suspend user.');
            }
        });
    }
}

// Admin Flagged Message Actions
function ignoreFlag(messageId) {
    if (confirm('Ignore this flagged message?')) {
        fetch(`/admin/ignore_flag/${messageId}`, { method: 'POST' })
        .then(response => {
            if (response.ok) {
                alert('Flag ignored.');
                window.location.reload();
            } else {
                alert('Failed to ignore flag.');
            }
        });
    }
}

function deleteFlaggedMessage(messageId) {
    if (confirm('Delete this flagged message?')) {
        fetch(`/admin/delete_flagged_message/${messageId}`, { method: 'POST' })
        .then(response => {
            if (response.ok) {
                alert('Flagged message deleted.');
                window.location.reload();
            } else {
                alert('Failed to delete flagged message.');
            }
        });
    }
}
