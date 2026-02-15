let passengerArray = [];

function togglePassengerForm() {
    const form = document.getElementById("passenger-form-card");
    if (form) {
        form.style.display = form.style.display === "none" ? "block" : "none";
    }
}

function updatePaymentStatus() {
    const payBtn = document.getElementById("pay-button");
    const warning = document.getElementById("error-msg");
    const hiddenInput = document.getElementById("passengers_json");

    if (passengerArray.length > 0) {
        payBtn.disabled = false;
        payBtn.style.opacity = "1";
        warning.style.display = "none";
    } else {
        payBtn.disabled = true;
        payBtn.style.opacity = "0.5";
        warning.style.display = "block";
    }
    // Convert array to string for Flask
    hiddenInput.value = JSON.stringify(passengerArray);
}

function addPassengerToList() {
    // Get values from the card
    const name = document.getElementById("p_name").value;
    const age = document.getElementById("p_age").value;
    const gender = document.getElementById("p_gender").value;
    const birth = document.getElementById("p_birth").value;

    if (!name || !age) {
        alert("Please fill in Name and Age.");
        return;
    }

    const passengerId = Date.now();
    const passengerObj = { id: passengerId, name, age, gender, birth };
    passengerArray.push(passengerObj);

    // Create the summary display
    const container = document.getElementById("passenger-list-container");
    const box = document.createElement("div");
    box.className = "passenger-summary-box";
    box.id = `p-card-${passengerId}`;
    box.style.cssText = "background: #222; border: 1px solid #444; padding: 10px; margin-bottom: 10px; display: flex; justify-content: space-between;";

    box.innerHTML = `
        <div>
            <strong>${name}</strong> (${age}, ${gender})<br>
            <small style="color: #888;">Berth: ${birth}</small>
        </div>
        <button type="button" onclick="removePassenger(${passengerId})" style="background:red; color:white; border:none; padding:5px;">✕</button>
    `;

    container.appendChild(box);

    // Reset and hide form
    document.getElementById("p_name").value = "";
    document.getElementById("p_age").value = "";
    togglePassengerForm();
    updatePaymentStatus();
}

function removePassenger(id) {
    passengerArray = passengerArray.filter((p) => p.id !== id);
    const element = document.getElementById(`p-card-${id}`);
    if (element) element.remove();
    updatePaymentStatus();
}