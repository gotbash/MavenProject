package testCases;

import java.util.concurrent.TimeUnit;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.support.PageFactory;

import pageobjects.Login;
import pageobjects.Profile;

public class Login_TC {

    static WebDriver driver;

    public static void main(String[] args) {

        driver = new ChromeDriver();

        driver.manage().timeouts().implicitlyWait(10, TimeUnit.SECONDS);
        driver.get("http://176.36.27.131:8180/#/");

        //Instantiating Login & Profile page using initElements()
        Login loginPg = PageFactory.initElements(driver, Login.class);
        Profile profilePg = PageFactory.initElements(driver, Profile.class);

        //Using the methods created in pages class to perform actions
        loginPg.LogIn_Action("thadmin", "tickethub");
        profilePg.verifyUser("---your username---");
        profilePg.logout_Action();

        driver.quit();
    }

}