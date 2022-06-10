package testdata;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.support.PageFactory;

import pageobjects.Login;
import pageobjects.Profile;

public class Testdata {

    static WebDriver driver;

    public static void main(String[] args) {

        driver = new ChromeDriver();

        driver.get("http://176.36.27.131:8180/#/");

        //Instantiating Login & Profile page using initElements()
        Login loginPg = PageFactory.initElements(driver, Login.class);
        Profile profilePg = PageFactory.initElements(driver, Profile.class);

        //Using the methods created in pages class to perform actions
        loginPg.LogIn_Action("thadmin", "tickethub");
        profilePg.verifyUser("---your username---");
        profilePg.logout_Action();

    }

}